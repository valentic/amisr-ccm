#!/usr/bin/env python3
"""Network bandwith monitor"""

##################################################################
#
#   Post network performance data collected by iperf3 
#
#   2023-08-21  Todd Valentic
#               Initial implementation.
#
##################################################################

import json
import subprocess

from datamonitor import DataMonitorComponent
from datamonitor import ConfigComponent

import jsonlib

class Scan(ConfigComponent):

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, 'scan', *p, **kw)

        self.cmd = self.config.get('cmd')

    def process(self):
        
        if not self.cmd:
            return None

        self.log.info('Scan start')

        status, output = subprocess.getstatusoutput(self.cmd)

        if status != 0:
            self.log.error('Problem running command')
            self.log.error('cmd: %s', self.cmd)
            self.log.error('status: %s', status)
            self.log.error('output: %s', output)
            return None

        self.log.info('Scan finished')

        return json.loads(output)

class IperfMonitor(DataMonitorComponent):
    """Iperf resource monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.scans = self.config.get_components('scans', factory=Scan)

    def sample(self):
        """Collect data"""

        results = {}
        results['scans'] = {}
        results['meta'] = { "timestamp": self.now(), "version": 1 }

        for scan in self.scans.values():
            data = scan.process()

            if data:
                results[scan.name] = data

        if not results:
            return None

        self.put_cache("iperf", results)

        return jsonlib.output(results)
