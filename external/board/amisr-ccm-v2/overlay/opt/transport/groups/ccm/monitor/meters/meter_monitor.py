#!/usr/bin/env python3
"""Meter monitor"""

##################################################################
#
#   Post meter state messages.
#
#   2023-08-03  Todd Valentic
#               Initial implementation.
#
##################################################################

import datetime
import xmlrpc.client

from datamonitor import DataMonitorComponent

import jsonlib

class MeterMonitor(DataMonitorComponent):
    """Meter monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        service_name = self.config.get("status.service") 
        method_name = self.config.get("status.method")
        
        meter_service = self.directory.connect(service_name)

        self.get_state = getattr(meter_service, method_name)

    def sample(self):
        """Collect data"""

        try:
            results = self.get_state()
        except xmlrpc.client.Fault as err:
            self.log.error("%s", err)
            results = None

        return jsonlib.output(results)
