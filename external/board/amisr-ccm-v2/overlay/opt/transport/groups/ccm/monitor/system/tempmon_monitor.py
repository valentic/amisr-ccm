#!/usr/bin/env python3
"""Control by web temperature monitor"""

##########################################################################
#
#   Read status from the ControlByWeb temperature monitors
#
#   The status can be read as an XML file from:
#
#       http://<host>/state.xml
#
#   2014-07-17  Todd Valentic
#               Initial implementation
#
#   2017-06-12  Todd Valentic
#               Extended to handle multiple sensors
#
#   2023-10-13  Todd Valentic
#               Updated for python3 / transport3
#               Integrate into CCM environment 
#
#   2024-03-04  Todd Valentic
#               Use timeout when making request
#
##########################################################################

import requests 
import xml.etree.ElementTree as et

import jsonlib

from datatransport import ConfigComponent
from datamonitor import DataMonitorComponent

class Station(ConfigComponent):

    def __init__(self, *args, **kwargs):
        ConfigComponent.__init__(self, "station", *args, **kwargs)

        self.host = self.config.get("host")
        self.url = self.config.get("url")
        self.timeout = self.config.get_timedelta("timeout", '5s') 
        self.timeout = self.timeout.total_seconds()

        self.log.info("Watching: %s", self.url)

    def process(self):
        """Download sensor data"""

        try:
            r = requests.get(self.url, timeout=self.timeout)
        except requests.exceptions.RequestException as err:
            self.log.error("Problem reading: %s", err)
            return None

        if r.status_code != 200:
            self.log.error("Failed to get record: %s", r.status_code)
            return None

        results = {}

        xml = et.fromstring(r.text)

        return jsonlib.parse_xml(xml)

class TemperatureMonitor(DataMonitorComponent):
    """Temperature data monitor"""

    def __init__(self, *args, **kwargs):
        DataMonitorComponent.__init__(self, *args, **kwargs)

        self.stations = self.config.get_components("stations", factory=Station)
        self.cache_key = "tempmon"

    def sample(self):
        """Read temperatures from stations"""

        network = self.get_cache("network")

        if not network:
            return None

        results = {}

        for station in self.stations.values():
           
            if station.host not in network:
                continue

            data = station.process()

            if data:
                results[station.name] = data

        if not results:
            return None

        self.put_cache(self.cache_key, results)

        return jsonlib.output(results)

