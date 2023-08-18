#!/usr/bin/env python3
"""Data monitor shell to run multiple data monitor components"""

##########################################################################
#
#   Data monitor shell
#
#   2023-08-07  Todd Valentic
#               Initial implementation. Generalized from system group.
#
##########################################################################

import importlib
import sys

from datatransport import ProcessClient
from sapphire_config import Rate

class DataMonitorShell(ProcessClient):
    """Data Monitor Shell"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.monitors = self.config.get_components("monitors", factory=self.monitor_factory)
        self.steprate = self.config.get_rate('steprate', Rate(60, True, 0, True))

    def monitor_factory(self, name, config, parent, **kw):
        """Factory function"""

        key = self.config.get("monitor.*.type", name)
        key = self.config.get("monitor.default.type", key)
        key = self.config.get(f"monitor.{name}.type", key)

        self.log.info("creating monitor: %s (%s)", key, name)

        module_name, class_name = key.rsplit(".", 1)
        file_path = self.config.get_path("group.home") / f"{module_name}.py"

        module = importlib.import_module(module_name)
        factory = getattr(module, class_name)

        return factory(name, config, parent, **kw)

    def main(self):
        """Main application"""

        self.log.info("Starting main application")


        steppers = [monitor.step() for monitor in self.monitors.values()]
        rate = Rate(60, True, 0, True)

        while self.wait(self.steprate):
            for stepper in steppers:
                try:
                    next(stepper)
                except StopIteration:
                    pass

        self.log.info("Exiting main application")


if __name__ == "__main__":
    DataMonitorShell(sys.argv).run()
