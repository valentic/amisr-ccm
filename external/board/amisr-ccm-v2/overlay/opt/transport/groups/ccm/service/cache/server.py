#!/usr/bin/env python3
"""Cache Service"""

##########################################################################
#
#   Caching service
#
#   This service is used to cache values between clients.
#
#   2009-11-03  Todd Valentic
#               Initial implementation
#
#   2009-11-11  Todd Valentic
#               Incorporate config lookup (replaced the separate
#                   config service).
#
#   2018-06-08  Todd Valentic
#               Integrate with event service
#
#   2019-07-19  Todd Valentic
#               Add get_or_default
#
#   2021-06-30  Todd Valentic
#               Add timeout and expire processing
#               Add clear
#
#   2021-07-21  Todd Valentic
#               Simplify timeouts to always be in secs
#
#   2023-06-03  Todd Valentic
#               Update for transport 3 / python 3
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import XMLRPCServer
from datatransport import Directory


class Server(ProcessClient):
    """Cache Service"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.xmlserver = XMLRPCServer(self, callback=self.expire)
        self.directory = Directory(self)

        self.xmlserver.register_function(self.get_value, "get")
        self.xmlserver.register_function(self.get_value_default, "get_or_default")
        self.xmlserver.register_function(self.get_age, "get_age")
        self.xmlserver.register_function(self.put_value, "put")
        self.xmlserver.register_function(self.list)
        self.xmlserver.register_function(self.lookup)
        self.xmlserver.register_function(self.clear_value, "clear")
        self.xmlserver.register_function(self.set_timeout, "set_timeout")
        self.xmlserver.register_function(self.get_timeout, "get_timeout")
        self.xmlserver.register_function(self.clear_timeout, "clear_timeout")

        self.event = self.directory.connect("event")

        self.cache = {}
        self.timestamp = {}
        self.timeouts = {}

    def expire(self):
        """Expire entries with a timeout"""

        for key, timeout in self.timeouts.items():
            if key in self.cache:
                if self.get_age(key) > timeout:
                    self.clear_value(key)

    def set_timeout(self, key, secs):
        """Set timeout for an entry"""

        self.timeouts[key] = secs

    def clear_timeout(self, key):
        """Remove timeout for an entry"""

        if key in self.timeouts:
            del self.timeouts[key]

    def get_timeout(self, key):
        """Return the timeout for an entry"""

        return self.timeouts.get(key)

    def put_value(self, key, value):
        """Store entry into cache"""

        self.log.debug("put %s %s", key, value)
        self.cache[key] = value
        self.timestamp[key] = self.now()
        self.event.notify(key, value)
        return True

    def get_value(self, key):
        """Get an entry from the cache"""

        return self.cache[key]

    def get_value_default(self, key, default):
        """Get an entry or default if not in cache"""

        if key in self.cache:
            return self.cache[key]

        return default

    def get_age(self, key):
        """Get the age of an entry"""

        age = self.now() - self.timestamp[key]
        return age.total_seconds()

    def clear_value(self, key):
        """Remove an entry from the cache"""

        if key in self.cache:
            del self.cache[key]
            del self.timestamp[key]

        return True

    def list(self):
        """List entries in cache"""

        return list(self.cache.keys())

    def lookup(self, keyword):
        """Lookup entry in process config"""

        return self.config.get(keyword)

    def main(self):
        """Main application"""

        self.xmlserver.main()


if __name__ == "__main__":
    Server(sys.argv).run()
