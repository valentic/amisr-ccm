#!/usr/bin/env python3
"""Watchdog data monitor"""

############################################################################
#
#   Watchdog data monitor
#
#   This script monitors the process group clients and reports any that
#   were started but have seemed to stop running (they are registered but
#   don't show up as an active process). In this case, the client is
#   restarted. Based on the standard watchdog code.
#
#   2009-11-12  Todd Valentic
#               Initial implementation
#
#   2013-03-04  Todd Valentic
#               Migrate to DataMonitorComponent framework
#
#   2023-07-07  Todd Valentic
#               Updated for transport3 / python3
#
############################################################################

import pathlib

from datamonitor import DataMonitorComponent

class WatchdogMonitor(DataMonitorComponent):
    """Watchdog data monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.server = self.parent.server

    def get_client_pids(self):
        """Query server for expected client PIDs"""

        pids = {}

        for group in self.server.listgroups():
            for client, info in self.server.listclients(group).items():
                pid = info[1]
                if pid:
                    pids[pid] = (group, client)

        return pids

    def get_running_pids(self):
        """Get list of running PIDs on system"""

        proc = pathlib.Path('/proc')
        return [int(x.name) for x in proc.iterdir() if x.name.isdigit()]

    def restart(self, pid, group, client):
        """Restart client process"""

        self.log.info("Process %d (%s %s) is missing", pid, group, client)
        self.log.info("  Attempting to restart")

        try:
            self.server.startclient(group, client)
        except: # pylint: disable=bare-except
            self.log.info("  Error detected in client restart!")

    def sample(self):
        """Check processes"""

        self.log.debug("Checking processes")

        try:
            self.server.status()
        except: # pylint: disable=bare-except
            self.log.error("Cannot connect to the transport server!")
            return

        client_pids = self.get_client_pids()
        running_pids = self.get_running_pids()

        for pid in set(client_pids).difference(running_pids):
            group, client = client_pids[pid]
            self.restart(pid, group, client)
