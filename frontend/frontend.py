# -*- coding: utf-8 -*-
"""
Created on 13.06.2012

@author: karsten
"""

from datetime import datetime
import hashlib
import logging
import sys
import time

from flask import (Flask, abort, redirect, url_for, render_template, request, flash)
from flask.ext.login import (LoginManager, current_user, login_required, login_user, logout_user)
from flask.ext.runner import Runner
from gensim.corpora import Dictionary
from mongoengine import *

from appuser import AppUser
import jinja2_filters
from nyan.shared_modules.models.mongodb_models import (Vendor, User, Article, UserModel, ReadArticleFeedback)
from nyan.shared_modules.utils.helper import load_config

from flask_debugtoolbar import DebugToolbarExtension


#Configure logger
logging.basicConfig(format='-' * 80 + '\n' +
                           '%(asctime)s : %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n' +
                           '%(message)s\n' +
                           '-' * 80,
                    level=logging.DEBUG,
                    filename="log.txt")

#Flask app
app = Flask(__name__)
runner = Runner(app)

#salt for hashing etc.
SALT = u""

#Load non-FLASK config
config = load_config("config.yaml", app.logger)

#Flask config
try:
    SECRET_KEY = config['flask']['secret_key']
    DEBUG = config['flask']['debug']
except KeyError as e:
    app.logger.error("Malformed config." + "Could not get flask secret key and debug option: %s" % (e))
    sys.exit(1)

# For debugging
toolbar = DebugToolbarExtension(app)

app.config.from_object(__name__)

#Login manager
login_manager = LoginManager()

login_manager.login_view = "login"
login_manager.login_message = u"Please log in to access this page."
#login_manager.refresh_view = "reauth"

@login_manager.user_loader
def load_user(user_id):
    """
    Loads user from Database
    """
    try:
        user = User.objects(id=user_id).first()
    except Exception as inst:
        app.logger.error("Could not login user %s: %s" % (type(inst), type))
        return None

    if user is None:
        app.logger.error("No user found for %s" % user_id)
        return None

    return AppUser(user)


login_manager.init_app(app)

#Connect to mongo database
connect(config['database']['db-name'],
        username=config['database']['user'],
        password=config['database']['passwd'],
        port=config['database']['port'])


#jinja2 filter to test if vendor is in given subscription
def is_subscribed(vendor):
    if not current_user.is_authenticated():
        return False

    try:
        for v in current_user.mongodb_user.subscriptions:
            if v == vendor:
                return True
        return False
    except Exception as inst:
        app.logger.error("Error when checking subscription %s: %s" % (type(inst), inst))
        return False

#register jinja2 filters
app.jinja_env.filters['datetimeformat'] = jinja2_filters.datetimeformat
app.jinja_env.filters['datetimeformat_read'] = jinja2_filters.datetimeformat_read
app.jinja_env.filters['firstparagraph'] = jinja2_filters.firstparagraph
app.jinja_env.filters['prevdate'] = jinja2_filters.prevdate
app.jinja_env.filters['nextdate'] = jinja2_filters.nextdate
app.jinja_env.filters['start_timer'] = jinja2_filters.start_timer
app.jinja_env.filters['end_timer'] = jinja2_filters.end_timer

#jinja2 filter to get the range of a list
app.jinja_env.filters['range'] = lambda l, start, stop: l[start:stop]

#register jinja2 filters
app.jinja_env.tests['today'] = jinja2_filters.is_today

app.jinja_env.filters['is_subscribed'] = is_subscribed

#Dictionary
app.logger.debug("Load dictionary.")
try:
    dictionary_ = Dictionary.load(config["dictionary"])
except IOError as ioe:
    app.logger.error("Could not load dictionary %s: %s" % (config["dictionary"], ioe))
    dictionary_ = None
except KeyError as e:
    app.logger.error("Malformed config. Could not get path to dictionary: %s" % (e))
    dictionary_ = None
except Exception as inst:
    app.logger.error("Could not load dictionary %s. Unknown error %s: %s" % (config["dictionary"], type(inst), inst))
    dictionary_ = None


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated():
        return redirect(request.args.get("next") or url_for('top'))

    if request.method == 'POST':
        e_mail = request.form['e_mail'].lower()
        password = request.form['password']
        if e_mail is not None and password is not None:
            #get user from database
            try:
                start = time.time()
                users = User.objects(email=e_mail)
                user = users.first()
                end = time.time()

                app.logger.info("Getting user took %f.5 seconds." % (end - start))
            except Exception as inst:
                app.logger.error("Could not login user %s: %s" % (type(inst), type))
                raise abort(500)

            if user is None:
                app.logger.error("No user found for %s" % e_mail)
                flash('Username or password are not correct.', 'error')
            else:
                #check password
                m = hashlib.sha256()
                m.update(password.encode("UTF-8"))
                m.update(SALT.encode("UTF-8"))

                if m.hexdigest() == user.password:
                    app.logger.debug("Login %s" % e_mail)
                    login_user(AppUser(user))
                    return redirect(request.args.get("next") or url_for('top'))
                else:
                    flash('Username or password are not correct.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/all/')
@app.route('/all/<date>')
@login_required
def all(date=None):
    if date is None:
        date_ = datetime.now()
    else:
        date_ = datetime.fromtimestamp(time.mktime(time.strptime(date, u'%d-%m-%Y')))

    #check if user has any subscriptions
    if len(current_user.get_subscriptions()) == 0:
        return render_template('no_subscriptions.html', date=date_,
                               tab="all", user=current_user.get_user_data)

    #get articles
    articles_ = current_user.get_articles(date=date_)
    read_articles_ = current_user.get_read_articles(date=date_)

    if len(articles_) == 0:
        return render_template('no_news.html', date=date_,
                               tab="all", user=current_user.get_user_data)

    #render template
    return render_template('overview.html',
                           date=date_, tab="all",
                           articles=articles_,
                           read_articles=read_articles_)


@app.route('/read/<key>')
@login_required
def read(key):
    try:
        article_ = Article.objects(id=key).first()
    except ValidationError as ve:
        app.logger.error("Error on reading %s (%s): %s" % (key, type(ve), ve))
        article_ = None

    if article_ is None:
        return render_template('no_article.html', date=datetime.now())

    #save user feedback
    current_user.save_read_article_feedback(article=article_, score=1.0)

    #render read article view
    return render_template('read.html', article=article_, date=datetime.now())


@app.route('/top/')
@app.route('/top/<date>')
@login_required
def top(date=None):
    if date is None:
        date_ = datetime.now()
    else:
        date_ = datetime.fromtimestamp(time.mktime(time.strptime(date, u'%d-%m-%Y')))

    #check if user has any subscriptions
    if len(current_user.mongodb_user.subscriptions) == 0:
        return render_template('no_subscriptions.html', date=date_, tab="all", user=current_user.mongodb_user)

    #get articles
    articles_ = current_user.get_top_articles(date=date_, min_rating=config['rating'])

    if len(articles_) == 0:
        return render_template('no_news.html', date=date_, tab="top", user=current_user.mongodb_user)

    #render template
    return render_template('top_overview.html', date=date_, tab="top", articles=articles_)


@app.route('/register')
@login_required
def register():
    """
    Registers a new user to service.
    """
    #only Karsten is allowed to add a new user
    if current_user.get_email() != "test@testmail.com":
        return redirect(url_for('index'))

    return render_template('add_user.html', tab="", date=datetime.now())


@app.route('/subscriptions')
@login_required
def subscriptions():
    return render_template('subscriptions.html', tab="subscriptions", date=datetime.now(), vendors=Vendor.objects())


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html',
                           tab="profile",
                           date=datetime.now(),
                           user_model=current_user.get_trained_profile(),
                           dictionary=dictionary_)


@app.route('/ajax_change_password', methods=['POST'])
def ajax_change_password():
    if not current_user.is_authenticated():
        abort(403)

    old_password = request.form['old_password']
    new_password = request.form['new_password']
    new_password_repeat = request.form['new_password_repeat']

    #check old password
    m = hashlib.sha256()
    m.update(old_password.encode("UTF-8"))
    m.update(SALT.encode("UTF-8"))

    #old password is wrong
    if m.hexdigest() != current_user.mongodb_user['password']:
        abort(403)

    if new_password != new_password_repeat:
        abort(403)

    if new_password == "":
        abort(400)

    #change password
    m = hashlib.sha256()
    m.update(new_password.encode("UTF-8"))
    m.update(SALT.encode("UTF-8"))

    try:
        current_user.set_password(new_password=m.hexdigest())
    except OperationError as e:
        app.logger.error("Could not save password to database")
        abort(500)
    except Exception as inst:
        app.logger.error("Could not change password %s: %s" % (type(inst), type))
        abort(500)

    return ""


@app.route('/ajax_subscribe', methods=['POST'])
def ajax_subscribe():
    """
    Called remotely to subscribe current user to a vendor
    """
    if not current_user.is_authenticated():
        abort(403)

    vendor_id = request.form['vendor_id']
    app.logger.error("Subscribe user to %s" % vendor_id)
    try:
        new_vendor = Vendor.objects(id=vendor_id).first()
        current_user.add_vendor_to_subscriptions(new_vendor)
    except Exception as inst:
        app.logger.error("Could not subscribe user %s: %s" % (type(inst), type))
        abort(500)

    return ""


@app.route('/ajax_unsubscribe', methods=['POST'])
def ajax_unsubscribe():
    """
    Called remotely to unsubscribe current user from vendor
    """
    if not current_user.is_authenticated():
        abort(403)

    vendor_id = request.form['vendor_id']

    app.logger.error("Unsubscribe user from %s" % vendor_id)
    try:
        vendor = Vendor.objects(id=vendor_id).first()
        current_user.remove_vendor_from_subscriptions(vendor)
    except Exception as inst:
        app.logger.error("Could not unsubscribe user %s: %s" % (type(inst), type))
        abort(500)

    return ""


@app.route('/ajax_add_user', methods=['POST'])
def ajax_add_user():
    """
    Called remotely to add a new user.
    """
    if not current_user.is_authenticated():
        abort(403)

    name = request.form['name']
    email = request.form['email'].lower()
    new_password = request.form['new_password']
    new_password_repeat = request.form['new_password_repeat']

    if current_user.mongodb_user.email != "test@testmail.com":
        abort(403)

    #check passwords
    if new_password != new_password_repeat:
        abort(400)

    if new_password == "":
        abort(400)

    #hash password
    m = hashlib.sha256()
    m.update(new_password.encode("UTF-8"))
    m.update(SALT.encode("UTF-8"))

    #check if user with email address already exists
    users_with_same_email = User.objects(email=email)
    if len(users_with_same_email) > 0:
        abort(400)

    try:
        app.logger.debug("Adding new user %s" % name)

        #just pick the first article as feedback
        first_article = Article.objects().first()
        first_profile = UserModel(features=first_article.features)

        new_user = User(name=name, password=m.hexdigest(), email=email, learned_profile=[first_profile])
        new_user.save(safe=True)

        first_feedback = ReadArticleFeedback(user_id=new_user.id, article=first_article, score=1.0)
        first_feedback.save()

        app.logger.debug("...done.")
    except Exception as inst:
        app.logger.error("Could not add new user: %s: %s" % (type(inst), type))
        abort(500)

    return ""

#Start app
if __name__ == '__main__':
    #app.run(host='0.0.0.0')
    runner.run()
