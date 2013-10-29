# -*- test-case-name:  -*-

# Copyright (c) Cogfor
# See LICENSE for details.


"""
Test stomp
"""
import logging

import time
import sys
import socket
import json

import stomp


logger = logging.getLogger("main")
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)


class StompListener(object):
    def __init__(self):
        self.logger = logging.getLogger("main")
        self.stdout = sys.stdout

    @staticmethod
    def on_error(self, message):
        logger.error('received an error %s' % message)

    @staticmethod
    def on_message(headers, message):
        received_message = json.loads(message)
        logger.info("RECEIVED MESSAGE: %s" % received_message)

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

    def on_connecting(self, hosts_and_port):
        pass

    def __error(self, msg, end="\n"):
        self.stdout.write(str(msg) + end)

    def __sysout(self, msg, end="\n"):
        self.stdout.write(str(msg) + end)

    def on_send(self, headers, body):
	self.__print_async("SEND", headers, body)


def main_loop():
    while 1:
        # do your stuff...
        time.sleep(20)


if __name__ == '__main__':
    hosts = [('localhost', 61613)]

    connected = False
    trys = 5
    while not connected:
        try:
            trys -= 1

            conn = stomp.Connection(host_and_ports=hosts)
            conn.set_listener('', StompListener())
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

        message = '{"news_vendor": "engadget", "features": {"version": "ESA-1.0", "data": []}, "author": "Marc Perton", "headline": "Don\'t even bother trying to upgrade to Windows RT 8.1 today", "content": "", "clean_content": "", "link": "http://www.engadget.com/2013/10/19/dont-bother-trying-to-upgrade-to-windows-rt-8-1-today/?ncid=rss_truncated"}'
        conn.send(message, destination='queue/features')

        while 1:
            time.sleep(20)
