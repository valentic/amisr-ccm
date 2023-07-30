#!/usr/bin/env python3
"""Location Service"""

##########################################################################
#
#   Location service
#
#   This service provides the best estimate for the station
#   location using a variety of input sources (GPS, Iridium, etc).
#   The "best" one is the newest one in the priority order
#   having a valid position fix.
#
#   The output is a dictionary with the following fields:
#
#       latitude
#       longitude
#       src
#
#   2021-06-29  Todd Valentic
#               Initial implementation.
#
##########################################################################

import sys

from datatransport import ProcessClient, XMLRPCServer, Directory


class Server(ProcessClient):
    """Location Service"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.xmlserver = XMLRPCServer(self)
        self.main = self.xmlserver.main
        self.connect = Directory(self)

        self.xmlserver.register_function(self.best)

        self.cache = self.connect("cache")
        self.sources = self.config.get_list("sources")

    def best(self):
        """Return the best estimage from different sources"""

        cache_entries = self.cache.list()

        entry = None
        result = None

        for source in self.sources:
            if source not in cache_entries:
                continue

            entry = self.cache.get(source)

            if source == "gps" and entry["mode"] < 2:
                # no position fix
                continue

            if "latitude" not in entry:
                continue

            if "longitude" not in entry:
                continue

            result = {}

            result["src"] = source
            result["latitude"] = entry["latitude"]
            result["longitude"] = entry["longitude"]

            break

        return result


if __name__ == "__main__":
    Server(sys.argv).run()
