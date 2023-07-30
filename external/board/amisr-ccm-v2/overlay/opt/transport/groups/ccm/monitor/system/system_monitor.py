#!/usr/bin/env python3
"""System resource monitor"""

##################################################################
#
#   Post system health status messages.
#
#   2009-07-28  Todd Valentic
#               Initial implementation.
#
#   2009-09-04  Todd Valentic
#               Updated to use DataMonitor
#
#   2010-09-22  Todd Valentic
#               Include version information
#
#   2013-03-04  Todd Valentic
#               Migrated to use DataMonitorComponent
#
#   2017-10-16  Todd Valentic
#               Add save_output flag
#               Store into cache
#
#   2017-10-25  Todd Valentic
#               Fix type for save_output to be boolean
#
#   2019-06-10  Todd Valentic
#               Use new cache methods
#
##################################################################

import subprocess

from datamonitor import DataMonitorComponent


class SystemMonitor(DataMonitorComponent):
    """System resource monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.save_output = self.config.get_boolean("save_output", True)

        self.versions = "\n".join(
            [
                "[Versions]"
                f"release.version: {self.config.get('release.version')}"
                f"release.date: {self.config.get('release.date')}"
            ]
        )

    def sample(self):
        """Collect data"""

        status, output = subprocess.getstatusoutput("systemstatus.py")

        output += self.versions

        if status != 0:
            raise IOError(output)

        self.put_cache("system", output)

        if self.save_output:
            return output.encode('utf-8')

        return None
