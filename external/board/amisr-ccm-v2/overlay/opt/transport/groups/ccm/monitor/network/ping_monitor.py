#!/usr/bin/env python3
"""Network ping monitor"""

##################################################################
#
#   Post network ping data 
#
#   2023-08-22  Todd Valentic
#               Initial implementation.
#
##################################################################

import json
import subprocess

from datamonitor import DataMonitorComponent
from datamonitor import ConfigComponent

import pingkit
import jsonlib

class Host(ConfigComponent):

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, 'host', *p, **kw)

        hostname = self.config.get('hostname', self.name)
        count = self.config.get_int('count', 10)
        timeout = self.config.get_timedelta('timeout', 10).total_seconds() 

        self.pinger = pingkit.Pinger(hostname, count=count, timeout=timeout)

    def process(self):
        
        results = self.pinger.collect()

        if results:
            avg = results["round_trip_ms_avg"]
            loss = results["packet_loss_percent"]
            self.log.info("%d ms rtt, %.1f%% loss", avg, loss)
        else:
            self.log.info('--')

        return results 

class PingMonitor(DataMonitorComponent):
    """Ping resource monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.hosts = self.config.get_components('hosts', factory=Host)

    def sample(self):
        """Collect data"""

        results = {}
        results['hosts'] = {}
        results['meta'] = { "timestamp": self.now(), "version": 1 }

        for host in self.hosts.values():
            data = host.process()

            if data:
                results['hosts'][host.name] = data

        if not results['hosts']:
            return None

        self.put_cache("ping", results)

        return jsonlib.output(results)


