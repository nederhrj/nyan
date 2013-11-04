#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import logging
from mongoengine import *
from nyan.shared_modules.models.mongodb_models import *

""" Creates vendors in mongodb """

def add_vendors():
    for vendor in ["techcrunch", "allthingsd", "allfacebook", "androidandme", "anandtech", "boingboing", "bgr", "engadget", "cnn-europe", "dutchnews"]:
        logging.info("add vendor: " + vendor)
        vendor = Vendor(name=vendor, config="vendor config " + vendor)
        vendor.save()

if __name__ == '__main__':
    logging.basicConfig(filename='test.log',level=logging.DEBUG)

    try:
        connect("nyan_test")
    except Exception as e:
        logging.error("Could not connect to MongoDB due to error %s: %s" % (type(e), e))

    Vendor.objects().delete

    try:
        add_vendors()
    except Exception as e:
        logging.error("Could add vendor due to error %s: %s" % (type(e), e))

