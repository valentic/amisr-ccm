#!/usr/bin/env python3
"""Save log files"""

##################################################################
#
#   Save log files
#
#   2021-09-21  Todd Valentic
#               Initial implementation.
#
##################################################################

import io
import tarfile

from datamonitor import DataMonitorComponent

class LogMonitor(DataMonitorComponent):
    """Log files data monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.pathnames = self.config.get_list("path.logfiles")

    def sample(self):
        """Collect data"""

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tarball:
            for pathname in self.pathnames:
                tarball.add(pathname)

        return buffer.getvalue()
