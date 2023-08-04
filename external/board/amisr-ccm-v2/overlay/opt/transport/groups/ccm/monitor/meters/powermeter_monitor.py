#!/usr/bin/env python3
"""Power meter monitor"""

##################################################################
#
#   Post power meter (Acuvim II) state messages.
#
#   2023-08-02  Todd Valentic
#               Initial implementation.
#
##################################################################

import datetime
import xmlrpc.client

from datamonitor import DataMonitorComponent

import jsonlib

class PowerMeterMonitor(DataMonitorComponent):
    """Power meter monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.powermeter = self.directory.connect("powermeter")

    def sample(self):
        """Collect data"""
    
        try:
            results = self.powermeter.get_state() 
        except xmlrpc.client.Fault as err:
            self.log.error("%s", err)
            results = None 

        return jsonlib.output(results)
