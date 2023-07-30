#!/usr/bin/env python3
"""Power Data Monitor"""

##########################################################################
#
#   Power Data Monitor
#
#   A DataMonitor object with a schedule driven by the
#   current power level. We use the charge power input
#   measured by the SunSaver charge controller.
#
#   2016-08-11  Todd Valentic
#               Initial implementation.
#               Based on PowerDataMonitor
#
#   2023-07-017 Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import sys

import sunsaver

from datatransport import ProcessClient
from datatransport import ConfigComponent

from datamonitor import DataMonitorBase


class PowerDataMonitorBase(DataMonitorBase):
    """Power Data Monitor Base Class"""

    def __init__(self):
        DataMonitorBase.__init__(self)

        self.report_missing_location = True
        self.report_state = None

    def when_on(self):
        """On state handler"""

        schedule = self.cur_schedule

        # Swap schedules based on solar angle

        rate = schedule.get_rate("sample.rate", 60)

        self.log.debug("dumping schedule (%s)", schedule.name)
        for option in schedule.options():
            self.log.debug("  %s: %s", option, schedule.get(option))

        if self.is_power_good():
            rate = schedule.get_rate("power.good.sample.rate", rate)
            state = "power.good"

        else:
            rate = schedule.get_rate("power.low.sample.rate", rate)
            state = "power.low"

        self.cur_schedule.sample_rate = rate

        if self.report_state != state:
            self.log.info("State change: %s -> %s", self.report_state, state)
            if self.report_state:
                self.next_sample_time = None
            self.report_state = state

        DataMonitorBase.when_on(self)

    def get_power_watts(self):
        """Get output power (W)"""

        rawdata = self.get_cache.get("sunsaver")

        if rawdata is None:
            return 0

        data = sunsaver.Parse(rawdata)

        return data["power_out"]

    def is_power_good(self):
        """Test for sufficient power"""

        power_watts = self.get_power_watts()

        schedule = self.cur_schedule

        min_power_watts = schedule.get_float("power.good.watts", 20)

        if power_watts >= min_power_watts:
            self.log.debug("    power good %.1f >= %.1f", power_watts, min_power_watts)
            return True

        self.log.debug("    power low %.1f < %.1f", power_watts, min_power_watts)
        return False


class PowerDataMonitorComponent(PowerDataMonitorBase, ConfigComponent):
    """Power Data Monitor Component"""

    def __init__(self, *pos, **kw):
        ConfigComponent.__init__(self, "monitor", *pos, **kw)
        PowerDataMonitorBase.__init__(self)


class PowerDataMonitor(PowerDataMonitorBase, ProcessClient):
    """Power Data Monitor"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)
        PowerDataMonitorBase.__init__(self)

    def main(self):
        """Main application loop"""

        for _step in self.step():
            if not self.wait(self.schedule_rate):
                break


if __name__ == "__main__":
    PowerDataMonitor(sys.argv).run()
