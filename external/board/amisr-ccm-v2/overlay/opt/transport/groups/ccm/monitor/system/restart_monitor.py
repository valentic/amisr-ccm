#!/usr/bin/env python3
"""System restart"""

############################################################################
#
#   Restart Monitor
#
#   This script restarts the system by setting the restart.system flag at
#   at scheduled time. The scheduler is solar driven so that we only
#   restart the system during day at solar local noon, when we are idle.
#
#   2021-09-17  Todd Valentic
#               Initial implementation
#
#   2023-07-07  Todd Valentic
#               Updated for transport3 / python3
#
############################################################################

from solar_datamonitor import SolarDataMonitorComponent


class RestartMonitor(SolarDataMonitorComponent):
    """Restart Data Monitor"""

    def __init__(self, *pos, **kw):
        SolarDataMonitorComponent.__init__(self, *pos, **kw)

        self.flagfile = self.config.get_path("flagfile", "restart")

    def sample(self):
        """Write restart flag"""

        self.log.info("Writing restart flag: %s", self.flagfile)

        self.flagfile.write_text("restart", encoding="utf-8")
