#!/usr/bin/env python3
"""GPS Data Monitor"""

# pylint: disable=invalid-name

###################################################################
#
#   GPS Data Monitor
#
#   Read current position from gpsd.
#
#   2017-10-11  Todd Valentic
#               Initial implementation
#
#   2019-06-10  Todd Valentic
#               Use new cache methods
#               Add altitude
#
#   2021-06-23  Todd Valentic
#               Set cache timeout
#
#   2021-07-17  Todd Valentic
#               Add ability to save if position changes
#
#   2023-07-07  Todd Valentic
#               Updated for transport3 / python3
#
###################################################################

import json
import pathlib
import sys
import struct

from math import radians, cos, sin, asin, sqrt

import gpsd

from datamonitor import DataMonitor


def haversine(lat1, lon1, lat2, lon2):
    """Compute the haversine distance between points"""

    R = 3959.87433  # miles.  For Earth radius in kilometers use 6372.8 km

    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(dLat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dLon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return R * c


OUTPUT_CHANGED = "change"
OUTPUT_ALWAYS = "always"


class GPSMonitor(DataMonitor):
    """GPS Data Monitor"""

    def __init__(self, argv):
        DataMonitor.__init__(self, argv)

        cache_timeout = self.config.get_timedelta("cache.timeout")

        # always or change
        self.output_mode = self.get("output.mode", OUTPUT_ALWAYS)

        self.change_limit = self.get_float("change.limit", 20)
        self.cache_filename = pathlib.Path("position.dat")

        if cache_timeout:
            secs = cache_timeout.total_seconds()
            self.cacheService.set_timeout("gps", secs)
            self.log.info("Setting cache timeout to %s", cache_timeout)

        self.prev_position = self.load_position()

        self.log.info("Ready to start")

    def load_position(self):
        """Load position from cache"""

        try:
            contents = self.cache_filename.read_text("utf-8")
            return json.loads(contents)
        except: # pylint: disable=bare-except
            self.log.info("No previous position file")
            return None

    def save_position(self, data):
        """Save position to cache"""

        try:
            contents = json.dumps(vars(data), default=str)
            self.cache_filename.write_text(contents, encoding="utf-8")
        except: # pylint: disable=bare-except
            self.log.exception("Failed to save current position file")

    def update(self, data):
        """Position update"""

        # Add compatible field names for schedules
        data["latitude"] = data["lat"]
        data["longitude"] = data["lon"]
        data["altitude"] = data["alt"]
        data["timestamp"] = data["time"]

        self.putCache("gps", data)

    def has_moved(self, data):
        """Determine if we have moved"""

        if data.mode == 3:
            if self.prev_position:
                lat1 = data.lat
                lon1 = data.lon
                lat2 = self.prev_position["lat"]
                lon2 = self.prev_position["lon"]

                dist = haversine(lat1, lon1, lat2, lon2)

                self.log.debug("Moved %f m", dist)

                return dist > self.change_limit

            return True

        return False

    def sample(self):
        """Take a position reading"""

        try:
            gpsd.connect()
            packet = gpsd.get_current()
        except:  # pylint: disable=bare-except
            self.log.exception("Problem reading from gpsd")
            return None

        self.update(vars(packet))
        self.log.info(packet)

        if self.output_mode == OUTPUT_CHANGED:
            if self.has_moved(packet):
                self.log.info("Change detected")
                self.save_position(packet)
                self.prev_position = self.load_position()
                return packet
            return None
        
        return packet

    def write(self, output, timestamp, data):
        """Save data"""

        version = 1

        output.write(struct.pack("!B", version))
        output.write(struct.pack("!B", data.sats))
        output.write(struct.pack("!B", data.mode))
        output.write(struct.pack("!i", timestamp))
        output.write(struct.pack("!f", data.lat))
        output.write(struct.pack("!f", data.lon))
        output.write(struct.pack("!f", data.alt))
        output.write(struct.pack("!f", data.hspeed))
        output.write(struct.pack("!f", data.track))
        output.write(struct.pack("!f", data.climb))


if __name__ == "__main__":
    GPSMonitor(sys.argv).run()
