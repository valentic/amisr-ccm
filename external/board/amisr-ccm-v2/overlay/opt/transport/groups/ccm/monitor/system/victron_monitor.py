#!/usr/bin/env python3
"""Victron monitor"""

##################################################################
#
#   Post Victron state messages.
#
#   2023-08-02  Todd Valentic
#               Initial implementation.
#
##################################################################

import datetime

from datamonitor import DataMonitorComponent

import jsonlib

class VictronMonitor(DataMonitorComponent):
    """Victron monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.victron = self.directory.connect("victron")

    def sample(self):
        """Collect data"""

        results = self.victron.get_state() 

        return jsonlib.output(results)
