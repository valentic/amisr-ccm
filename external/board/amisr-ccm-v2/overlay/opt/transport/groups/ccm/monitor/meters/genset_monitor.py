#!/usr/bin/env python3
"""Genset monitor"""

##################################################################
#
#   Post Genset state messages.
#
#   2023-08-03  Todd Valentic
#               Initial implementation.
#
##################################################################

import datetime
import xmlrpc.client

from datamonitor import DataMonitorComponent

import jsonlib

class GensetMonitor(DataMonitorComponent):
    """Genset monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.genset = self.directory.connect("genset")

    def sample(self):
        """Collect data"""

        try:
            results = self.genset.get_state() 
        except xmlrpc.client.Fault as err:
            self.log.error("%s", err)
            results = None

        return jsonlib.output(results)
