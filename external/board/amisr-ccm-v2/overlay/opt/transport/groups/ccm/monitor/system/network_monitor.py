#!/usr/bin/env python3
"""Network Monitor"""

##################################################################
#
#   Monitor for hosts on the local network 
#
#   Scan for hosts that are currently online. 
#
#   2023-08-09  Todd Valentic
#               Initial implementation.
#
##################################################################

import json
import subprocess

from datamonitor import DataMonitorComponent

class NetworkMonitor(DataMonitorComponent):
    """Network data monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.cmd = self.config.get('scan.cmd')

        self.cache_key = "network"
    
    def sample(self):
        """Scan network for hosts that are online"""

        status, output = subprocess.getstatusoutput(self.cmd)

        if status != 0:
            self.log.error('Problem scanning network')
            self.log.error('cmd: %s', self.cmd)
            self.log.error('status: %s', status)
            self.log.error('output: %s', output)
            return None

        try:
            data = json.loads(output)
        except ValueError as err:
            self.log.error('Failed to parse output: %s', err)
            return None

        self.log.info('Scanning network: %d hosts online', len(data))

        self.put_cache(self.cache_key, data)

        return None
