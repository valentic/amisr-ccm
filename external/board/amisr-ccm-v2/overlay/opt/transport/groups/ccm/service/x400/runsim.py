#!/usr/bin/env python

##########################################################################
#
#   Run PDU Simulator
#
#   2023-07-09  Todd Valentic
#               Initial implementation
#
##########################################################################

import subprocess 
import sys

from datatransport import ProcessClient

class RunSim(ProcessClient):

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.cmd = self.config.get('simulator.cmd', 'x400sim')

    def main(self):

        proc = subprocess.Popen(self.cmd.split(), 
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
                )

        while self.wait(5): 
            pass

        if proc.poll() is None:
            proc.terminate()
            proc.wait()

if __name__ == '__main__':
    RunSim(sys.argv).run()


