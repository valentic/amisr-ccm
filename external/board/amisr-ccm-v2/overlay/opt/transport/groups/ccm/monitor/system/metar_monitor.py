#!/usr/bin/env python3
"""Monitor metar weather information"""

##################################################################
#
#   Monitor for new metar weather messages 
#
#   Post new metar reports for weather observations. 
#
#   2023-08-08  Todd Valentic
#               Initial implementation.
#
#   2024-03-03  Todd Valentic
#               Set timeout on requests get
#
##################################################################

from datetime import timezone
import hashlib
import json
import pathlib

from dateutil import parser
import requests

import jsonlib

from datatransport import ConfigComponent
from datamonitor import DataMonitorComponent

class Station(ConfigComponent):

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, 'station', *p, **kw)

        self.url = self.config.get('url')
        self.timeout = self.config.get_timedelta('timeout', '20s')
        self.timeout = self.timeout.total_seconds()

        self.log.info('Watching: %s', self.url)

    def process(self):
        """Download metar record"""
   
        try:
            r = requests.get(self.url, timeout=self.timeout)
        except requests.exceptions.RequestException as err:
            self.log.error('Problem downloading: %s', err)
            return None
        
        if r.status_code != 200:
            self.log.error('Failed to get record: %s', r.status_code)
            return None

        timestr, metar = r.text.split('\n')[:2]

        self.log.debug('%s %s', timestr, metar)

        timestamp = parser.parse(timestr).replace(tzinfo = timezone.utc)

        results = {
            'timestamp': timestamp,
            'metar': metar
        }

        return results

class MetarMonitor(DataMonitorComponent):
    """Metar network data monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.stations = self.config.get_components('stations', factory=Station)
        self.cache_key = "metar"

        self.marker_file = pathlib.Path("current.json")

        self.current = self.load_marker()
        self.current_checksum = self.compute_checksum(self.current) 

    def compute_checksum(self, contents):
        """Compute MD5 checksum"""

        if contents is None:
            return None
        return hashlib.md5(jsonlib.output(contents)).hexdigest()

    def load_marker(self):
        """Save current contents"""

        if self.marker_file.exists():
            contents = self.marker_file.read_text('utf-8')
            return json.loads(contents)

        return None

    def save_marker(self, value):
        """Load current contents"""

        contents = jsonlib.output(value)
        self.marker_file.write_bytes(contents)

    def sample(self):
        """Check for new metar data"""

        results = {}

        for station in self.stations.values():
            record = station.process()

            if record:
                results[station.name] = record

        if not results:
            return None

        new_checksum = self.compute_checksum(results)

        if new_checksum != self.current_checksum:
            self.log.info("Detected new metar records")
            self.log.info('Checksum old=%s, new=%s', self.current_checksum, new_checksum)
            self.save_marker(results)
            self.current = results 
            self.current_checksum = new_checksum
            self.put_cache(self.cache_key, results) 
            return jsonlib.output(results)

        return None
