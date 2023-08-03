#!/usr/bin/env python3
"""Data monitor shell to run multiple data monitor components"""

##########################################################################
#
#   Data monitor shell
#
#   2013-03-04  Todd Valentic
#               Initial implementation
#
#   2019-06-27  Todd Valentic
#               Add TS7250status
#
#   2021-06-30  Todd Valentic
#               Add tincan
#               Remove TS7250status for mango systems
#
#   2021-09-17  Todd Valentic
#               Add restart monitor
#               Add log monitor
#
#   2023-07-07  Todd Valentic
#               Updated for transport3 / python3
#
#   2023-07-24  Todd Valentic
#               Add PDUMonitor
#
#   2023-08-02  Todd Valentic
#               Add VictronMonitor
#               Add PowerMeterMonitor
#
##########################################################################

import sys

from datatransport import ProcessClient

from system_monitor import SystemMonitor
from schedule_monitor import ScheduleMonitor
from watchdog_monitor import WatchdogMonitor
from tincan_monitor import TincanMonitor
from restart_monitor import RestartMonitor
from log_monitor import LogMonitor
from pdu_monitor import PDUMonitor
from victron_monitor import VictronMonitor
from powermeter_monitor import PowerMeterMonitor


class DataMonitorShell(ProcessClient):
    """Data Monitor Shell"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.monitors = self.config.get_components("monitors", factory=self.monitor_factory)

    def monitor_factory(self, name, config, parent, **kw):
        """Factory function"""

        key = self.config.get("monitor.*.type", name)
        key = self.config.get("monitor.default.type", key)
        key = self.config.get(f"monitor.{name}.type", key)

        self.log.info("creating monitor: %s (%s)", key, name)

        factory = {
            "system": SystemMonitor,
            "schedules": ScheduleMonitor,
            "watchdog": WatchdogMonitor,
            "tincan": TincanMonitor,
            "restart": RestartMonitor,
            "log": LogMonitor,
            "pdu": PDUMonitor,
            "victron": VictronMonitor,
            "powermeter": PowerMeterMonitor
        }

        if key in factory:
            return factory[key](name, config, parent, **kw)

        raise ValueError(f"Unknown monitor: {key}")

    def main(self):
        """Main application"""

        self.log.info("Starting main application")

        steppers = [monitor.step() for monitor in self.monitors.values()]

        while self.wait(60, sync=True):
            for stepper in steppers:
                try:
                    next(stepper)
                except StopIteration:
                    pass

        self.log.info("Exiting main application")


if __name__ == "__main__":
    DataMonitorShell(sys.argv).run()
