# -*- test-case-name:  -*-

# Copyright (c) Cogfor
# See LICENSE for details.


"""


"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nyan.article_ranker.article_ranker import ArticleRanker
from nyan.feature_extractor.extractors import TfidfFeatureExtractor
from FillTestDatabase import fill_database, clear_database
import logging
import json

from mongoengine import *
from nyan.shared_modules.models.mongodb_models import *

import unittest
from nyan.shared_modules.utils.helper import load_config

logger = logging.getLogger("unittesting")

#Connect to test database
connect("nyan_test", port=27017)


class ArticleRankerTest(unittest.TestCase):

    def setUp(self):
        fill_database()
        config_ = load_config(file_path="/vagrant/config.yaml", logger=logger)
        self.feature_extractor = TfidfFeatureExtractor(prefix=config_['prefix'])
        self.ranker = ArticleRanker(extractor=self.feature_extractor)
        self.body = '{"news_vendor": "boingboing", ' \
                    '"features": ' \
                    '{"version": "TF-IDF-1.1", ' \
                    '"data": [[87, 1.0]]}, ' \
                    '"author": "David Pescovitz", ' \
                    '"headline": "Documentary about Astro Boy creator Osamu\\u00a0Tezuka",' \
                    ' "content": "<p class=\\"byline permalink\\"><a href=\\"http://boingboing.net/author/david_pescovitz\\" title=\\"Posts by David Pescovitz\\" rel=\\"author\\">David Pescovitz</a> at 9:33 am Wed, Oct 23, 2013   \\n\\n\\n\\n</p>", ' \
                    '"clean_content": "David Pescovitz at 9:33 am Wed, Oct 23, 2013 ",' \
                    ' "link": "http://rss.feedsportal.com/c/35208/f/653965/s/32d1ba95/sc/38/l/0Lboingboing0Bnet0C20A130C10A0C230Cdocumentary0Eabout0Eastro0Eboy0Ecr0Bhtml/story01.htm"}'
        self.article_as_dict = json.loads(self.body)

    def tearDown(self):
        #clear_database()
        pass

    def test_get_vendor(self):
        vendor = self.ranker.get_vendor(self.article_as_dict)

        self.assertEqual(self.article_as_dict.get('news_vendor'), vendor)

    def test_save_article(self):
        vendor = self.ranker.get_vendor(self.article_as_dict)
        stored_article = self.ranker.save_article(vendor, self.article_as_dict)

        self.assertEqual(stored_article.author, 'David Pescovitz')

    def test_save_rating(self):
        vendor = self.ranker.get_vendor(self.article_as_dict)
        stored_article = self.ranker.save_article(vendor, self.article_as_dict)
        user = User.objects(email="test@testmail.com").first()

        # Store number of ranked items
        ranked_articles = RankedArticle.objects(user_id=user.id)
        ranked_articles_before = ranked_articles.count()

        print user, vendor.name, stored_article.author

        # Store new ranked article
        self.ranker.save_rating(user=user, article=stored_article, rating=1.0)

        user.reload()
        ranked_articles_after = RankedArticle.objects(user_id=user.id).count()

        self.assertEqual(1, ranked_articles_after-ranked_articles_before)
        self.assertEqual(1.0, ranked_articles[ranked_articles_before].rating)

    def test_rank_article(self):
        pass
        #some error in gensim. probably because some features are not quite right
        self.ranker.rank_article(self.article_as_dict)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
