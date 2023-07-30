#!/usr/bin/env python2

import modem
import signal
import optparse
import logging
import Queue
import threading
import time

class Object(object):
    pass

class ServiceExit(Exception):
    pass

def serviceShutdown(signum,frame):
    raise ServiceExit

class ModemThread(threading.Thread):

    def __init__(self,config):
        threading.Thread.__init__(self,name='Modem')

        self.config = config
        self.runEvent = config.runEvent
        self.txQueue = config.txQueue
        self.rxQueue = config.rxQueue
        self.log = config.log

        self.modem = modem.Modem('iridium',self.log,isAlive=self.runEvent.isSet)

    def wait(self,secs):

        endtime = time.time() + secs

        while time.time()<endtime and self.runEvent.isSet():
            time.sleep(1)

    def run(self):

        self.log.info('Start modem thread')

        while self.runEvent.isSet():
            try:
                msg = self.txQueue.get(timeout=1)
            except Queue.Empty:
                msg = None

            if msg:
                self.modem.writeMessage(msg)
                self.log.info('Queuing outbound message')

            try:
                inboundMessages = self.modem.exchangeSBD()
            except StopIteration:
                continue

            if inboundMessages:
                self.log.info('Received %s messages' % len(inboundMessages))

            for msg in inboundMessages:
                self.rxQueue.put(msg)

            self.wait(60)

def Main(config):

    signal.signal(signal.SIGTERM,serviceShutdown)
    signal.signal(signal.SIGINT,serviceShutdown)

    config.runEvent = threading.Event()
    config.txQueue = Queue.Queue()
    config.rxQueue = Queue.Queue()

    config.runEvent.set()

    try:
        modemThread = ModemThread(config)
        modemThread.start()

        while True:
            try:
                msg = config.rxQueue.get(False)
            except Queue.Empty:
                time.sleep(1)
                continue

            print 'Received message:',msg

    except ServiceExit:

        config.runEvent.clear()

        modemThread.join()

    config.log.info('Main exit')

def ParseArgs():

    usage = '%PROG [OPTIONS]'

    parser = optparse.OptionParser(usage=usage)

    parser.add_option('-v','--verbose',dest='verbose',
                        default=False,action='store_true',
                        help='Verbose output'
                        )

    return parser.parse_args()

if __name__ == '__main__':

    options,args = ParseArgs()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    config = Object()
    config.options = options
    config.log = logging

    Main(config)


