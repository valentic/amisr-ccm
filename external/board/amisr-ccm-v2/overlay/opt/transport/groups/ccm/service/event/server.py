#!/usr/bin/env python3
"""Event Notification Service"""

##########################################################################
#
#   Event Notification Service
#
#   This service implements the observer pattern for
#   distributing events between clients.
#
#   See: http://en.wikipedia.org/wiki/Observer_pattern
#
#   2006-10-29  Todd Valentic
#               Initial implementation.
#
#   2007-04-16  Todd Valentic
#               Fixed bug in unregister if event not registered.
#
#   2023-06-03  Todd Valentic
#               Update for transport 3 / python 3
#               Only log no observers in debug
#
##########################################################################

import pathlib
import queue
import socket
import sys
import xmlrpc.client

from threading import Thread

from datatransport import ProcessClient
from datatransport import XMLRPCServer
from datatransport import AccessMixin

socket.setdefaulttimeout(5)

# pylint: disable=bare-except


class WorkerThread(Thread, AccessMixin):
    """Worker thread to senf event notifications"""

    def __init__(self, parent):
        Thread.__init__(self)
        AccessMixin.__init__(self, parent)

        self.queue = self.parent.queue

    def run(self):
        """Main thread"""

        self.log.info("Worker thread starting")

        while self.is_running():
            try:
                event, signature, args = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            url, method = signature

            try:
                client = xmlrpc.client.ServerProxy(url)
                getattr(client, method)(*args)
            except:
                self.log.exception(
                    "Problem notifying %s for %s (%s)", signature, event, args
                )

        self.log.info("Worker thread exiting")


class Server(ProcessClient):
    """Event Service"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.xmlserver = XMLRPCServer(self)

        self.xmlserver.register_function(self.register)
        self.xmlserver.register_function(self.unregister)
        self.xmlserver.register_function(self.notify)

        self.xmlserver.register_function(self.list_observerss)
        self.xmlserver.register_function(self.list_events)
        self.xmlserver.register_function(self.remove_event)

        # Private methods used for testing

        self.xmlserver.register_function(self.testport)

        self.save_cache = pathlib.Path("event")

        self.load_events()

        self.queue = queue.Queue()
        self.thread = WorkerThread(self)
        self.thread.start()

    def load_events(self):
        """Load event list cache"""

        self.events = {}

        if not self.save_cache.exists():
            return

        with self.save_cache.open("r", encoding="utf-8") as f:
            for line in f:
                event, url, method = line.split()
                self.add_observer(event, url, method)

    def save_events(self):
        """Save event list cache"""

        with self.save_cache.open("w", encoding="utf-8") as f:
            for event, observers in self.events.items():
                for url, method in observers:
                    print(event, url, method, file=f)

    def remove_event(self, event):
        """Remove event"""

        if not event in self.events:
            return

        self.log.info("Removing event: %s", event)

        del self.events[event]
        self.save_events()

    def register(self, event, url, method):
        """Subscribe to event"""

        self.add_observer(event, url, method)
        self.save_events()
        return 1

    def add_observer(self, event, url, method):
        """Add observer to event"""

        if event not in self.events:
            self.events[event] = []
        signature = (url, method)
        if signature not in self.events[event]:
            self.events[event].append(signature)

    def unregister(self, event, url, method):
        """Unsubscribe from event"""

        signature = (url, method)

        if event in self.events:
            try:
                self.events[event].remove(signature)
            except:
                pass

            if self.events[event] == []:
                del self.events[event]

        self.save_events()
        return 1

    def list_events(self):
        """List events"""

        return list(self.events.keys())

    def list_observerss(self, event):
        """List subscribers to an event"""

        return self.events[event]

    def notify(self, event, *args):
        """Senf a notification for event"""

        if event not in self.events:
            self.log.debug("Sending event %s", event)
            self.log.debug("  - no observers registered")
            return 1

        self.log.info("Sending event %s", event)

        for signature in self.events[event]:
            self.queue.put((event, signature, args))

        return 1

    def testport(self, msg):
        """Test receipt of event notification"""

        self.log.info("Testport: msg=%s", msg)
        return 1

    def main(self):
        """Main application"""

        self.xmlserver.main()

        # Need to wait for worker threads

        self.thread.join()

        self.log.info("Finished")


if __name__ == "__main__":
    Server(sys.argv).run()
