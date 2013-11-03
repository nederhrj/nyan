#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Karsten Jeschkies <jeskar@web.de>

The MIT License (MIT)
Copyright (c) 2012-2013 Karsten Jeschkies <jeskar@web.de>

Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the "Software"), to deal in 
the Software without restriction, including without limitation the rights to use, 
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the 
Software, and to permit persons to whom the Software is furnished to do so, 
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import json
import logging
import socket
import sys
import time

from mongoengine import *
import stomp
import yaml

from nyan.article_ranker.article_ranker import ArticleRanker
from nyan.shared_modules.feature_extractor.extractors import EsaFeatureExtractor, TfidfFeatureExtractor
from nyan.shared_modules.utils.daemon import Daemon


"""
The Article Ranker receives messages via STOMP from the Feature Extractor.

The messages include article details, the content and the extracted features.
Articles will be saved to database and ranked for each user. They will be marked
as top articles if their rank is high enough.
"""

logger = logging.getLogger("main")


class StompListener(object):
    def __init__(self, config):
        self.config_ = config
        self.logger = logging.getLogger("main")
        self.stdout = sys.stdout

        # Connect to mongo database
        try:
            connect(config['database']['db-name'],
                    username=config['database']['user'],
                    password=config['database']['passwd'],
                    port=config['database']['port'])
        except ConnectionError as e:
            logger.error("Could not connect to mongodb: %s" % e)
            sys.exit(1)

        logger.info("Load feature extractor.")
        try:
            self.feature_extractor_ = TfidfFeatureExtractor(prefix=self.config_["prefix"])
        except Exception as inst:
            logger.error("Could not load feature extractor."
                         "Unknown error %s: %s" % (type(inst), inst))
            sys.exit(1)

        self.ranker = ArticleRanker(extractor=self.feature_extractor_)

    def rank_article(self, article_as_dict):
        self.ranker.rank_article(article_as_dict)

    @staticmethod
    def on_error(self, message):
        logger.error('received an error %s' % message)

    def on_message(self, headers, message):
        received_message = json.loads(message)

        #save and rank article
        logger.info("*Ranked article* -> " + message)
        self.rank_article(received_message)

    def __print_async(self, frame_type, headers, body):
        """
        Utility function to print a message and setup the command prompt
        for the next input
        """
        self.__sysout("\r  \r", end='')
        self.__sysout(frame_type)
        for header_key in headers.keys():
            self.__sysout('%s: %s' % (header_key, headers[header_key]))
        self.__sysout('')
        self.__sysout(body)
        self.__sysout('> ', end='')
        self.stdout.flush()

    def on_connected(self, headers, body):
        self.__print_async("CONNECTED", headers, body)

    def __error(self, msg, end="\n"):
        self.stdout.write(str(msg) + end)

    def __sysout(self, msg, end="\n"):
        self.stdout.write(str(msg) + end)

    def on_send(self, headers, body):
        self.__print_async("SEND", headers, body)


class ArticleRankerDaemon(Daemon):
    def __init__(self, pidfile, config_file=None, log_file=None):

        logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG, filename=log_file)
        try:
            if config_file is not None:
                stream = file(config_file, 'r')
                self.config_ = yaml.load(stream)
                stream.close()
            else:
                self.config_ = None
        except IOError as e:
            print "Could not open %s: %s" % (config_file, e)
            sys.exit(1)
        except Exception as inst:
            print "Unknown error %s: %s" % (type(inst), inst)
            sys.exit(1)

        super(ArticleRankerDaemon, self).__init__(pidfile)

    def run(self):

        logger = logging.getLogger("main")

        if self.config_ is None:
            logger.error("No config.")
            sys.exit(1)

        hosts = [('localhost', 61613)]

        connected = False
        trys = 5
        while not connected:
            try:
                trys -= 1

                conn = stomp.Connection()
                conn.set_listener('', StompListener(self.config_))
                conn.start()
                conn.connect()

                conn.subscribe(destination='queue/features', ack='auto')
                connected = True
            except stomp.exception.ConnectFailedException:
                if trys > 0:
                    pass
                else:
                    logger.error("Could not connect to STOMP broker")
                    sys.exit(1)
            except socket.error:
                pass

        if connected:
            logger.info("Connected to STOMP broker")
            while 1:
                time.sleep(20)


if __name__ == "__main__":
    from optparse import OptionParser

    p = OptionParser()
    p.add_option('-c', '--config', action="store", dest='config',
                 help="specify config file")
    p.add_option('-d', action="store_true", dest='daemonize',
                 help="run the server as a daemon")
    p.add_option('-l', '--log', action="store", dest='log',
                 help="specify log file")
    p.add_option('-p', '--pidfile', dest='pidfile',
                 default='/tmp/daemon-article-ranker.pid',
                 help="store the process id in the given file. Default is "
                      "/tmp/daemon-article-ranker.pid")
    (options, args) = p.parse_args()

    daemon = ArticleRankerDaemon(options.pidfile, options.config, options.log)
    if len(sys.argv) >= 2:
        if 'start' == sys.argv[1]:
            if not options.config or not options.log:
                print "No config or logfile set."
                sys.exit(2)
            elif options.daemonize:
                daemon.start()
            else:
                daemon.run()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            if not options.config or not options.log:
                print "No config or logfile set."
                sys.exit(2)
            else:
                daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart options" % sys.argv[0]
        sys.exit(2)
