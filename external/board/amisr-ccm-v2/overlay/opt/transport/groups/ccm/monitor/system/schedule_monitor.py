#!/usr/bin/env python3
"""Monitor schedule changes"""

##################################################################
#
#   Monitor for schedule changes
#
#   2011-05-16  Todd Valentic
#               Initial implementation.
#
#   2013-03-04  Todd Valentic
#               Migrated to use DataMonitorComponent
#
#   2023-07-07  Todd Valentiv
#               Updated for transport3 / python3
#
##################################################################

import io
import glob
import hashlib
import pathlib
import tarfile

from datamonitor import DataMonitorComponent


class ScheduleMonitor(DataMonitorComponent):
    """Schedule data monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.schedule_path = self.config.get_path('path.schedules')
        self.checksum_path = pathlib.Path(f"{self.name}-checksum")

        self.load_checksum()

    def load_checksum(self):
        """Load checksum"""

        try:
            self.checksum = self.checksum_path.read_text('utf-8')
        except: # pylint: disable=bare-except
            self.checksum = None

    def save_checksum(self, checksum):
        """Save checksum"""

        self.checksum = checksum

        self.checksum_path.write_text(checksum, encoding="utf-8")

    def sample(self):
        """Save log files"""

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tarball:

            for filename in self.schedule_path.glob("*.conf"):
                tarball.add(filename)

        output = buffer.getvalue()
        checksum = hashlib.md5(output).hexdigest()

        if checksum != self.checksum:
            self.log.info("Detected modified schedules")
            self.save_checksum(checksum)
            return output

        return None
