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

from datamonitor import DataMonitorComponent

import jsonlib

class PowerMeterMonitor(DataMonitorComponent):
    """Power meter monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.powermeter = self.directory.connect("powermeter")

    def sample(self):
        """Collect data"""

        results = self.powermeter.get_state() 

        return jsonlib.output(results)
