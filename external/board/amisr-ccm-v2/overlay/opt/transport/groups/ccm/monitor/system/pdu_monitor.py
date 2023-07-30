#!/usr/bin/env python3
"""System resource monitor"""

##################################################################
#
#   Post PDU status messages.
#
#   2023-07-24  Todd Valentic
#               Initial implementation.
#
##################################################################

import json

from datamonitor import DataMonitorComponent


class PDUMonitor(DataMonitorComponent):
    """PDU status monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.pductl = self.directory.connect("pductl")

    def sample(self):
        """Collect data"""

        results = {"status": self.pductl.get_status(), "state": self.pductl.get_state()}

        return json.dumps(results).encode("utf-8")
