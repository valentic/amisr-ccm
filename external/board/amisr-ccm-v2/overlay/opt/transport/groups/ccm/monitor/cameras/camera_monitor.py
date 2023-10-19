#!/usr/bin/env python3
"""Camera monitor"""

##################################################################
#
#   Take images from a camera 
#
#   Periodically take an image from a camera. The exact cammand is
#   given as a parameter, so a variety of camera types can be 
#   supported. It assumes that the necessary resources have been
#   enabled elsewhere (i.e. network camera is on).
#
#   It is also assumed that the command outputs directly to
#   the appropriate location to avoid multiple writes.
#
#   2023-08-02  Todd Valentic
#               Initial implementation.
#
##################################################################

import sys
import shutil
import subprocess

from datamonitor import DataMonitorComponent

class CameraMonitor(DataMonitorComponent):
    """Camera monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.capture_cmd = self.config.get('capture.cmd')
        self.capture_output = self.config.get_path('capture.output')
        self.needed_resources = self.config.get('resources')

        self.log.info("Capture cmd: %s", self.capture_cmd)
        self.log.info("Capture output: %s", self.capture_output)

    def is_on(self):

        if not self.needed_resources:
            return True

        state = self.get_state('device', 'camera-poe')

        return state == "on"

    def going_off_to_on(self):
        """Off to on handler"""

        self.set_resources(self.needed_resources)

    def going_on_to_off(self):
        """On to off handler"""

        self.clear_resources()

    def sample(self):
        """Collect data"""

        cmd = self.capture_cmd
        status, output = subprocess.getstatusoutput(cmd)

        if status != 0:
            self.log.error('Problem capturing image')
            self.log.error('cmd: %s', cmd)
            self.log.error('status: %s', status)
            self.log.error('output: %s', output)
            return None

        if self.capture_output.exists():
            return self.capture_output

        return None 

    def write(self, output, timestamp, localfile):
        with localfile.open('rb') as src:
            shutil.copyfileobj(src, output)
        localfile.unlink()

if __name__ == '__main__':
    CameraMonitor(sys.argv).run()
