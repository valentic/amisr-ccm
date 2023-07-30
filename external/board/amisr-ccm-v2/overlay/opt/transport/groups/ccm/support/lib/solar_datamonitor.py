#!/usr/bin/env python3
"""Solar Data Monitor"""

##########################################################################
#
#   Solar Data Monitor
#
#   A DataMonitor object with a schedule driven by the
#   location of the sun. We use the current GPS location
#   to compute solar local noon and operate within a
#   window around it. We also have the ability to only
#   run on certain days.
#
#   2009-11-05  Todd Valentic
#               Initial implementation
#
#   2009-11-09  Todd Valentic
#               Change some log output from info -> debug
#
#   2010-01-22  Todd Valentic
#               Incorporate loadable schedules.
#
#   2010-03-16  Todd Valentic
#               Fix solar angle check
#               Schedule framework moved to DataMonitor
#
#   2010-10-25  Todd Valentic
#               Repeat days should check transit_time
#
#   2011-08-25  Todd Valentic
#               Handle solar angle and window_max = None
#               Use iridium position data if no GPS data
#
#   2013-03-04  Todd Valentic
#               Break into Base and Component classes
#
#   2021-06-30  Todd Valentic
#               Use location service
#
#   2023-07-05  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import sys

import ephem

from datatransport import ProcessClient
from datatransport import ConfigComponent

from datamonitor import DataMonitorBase


class SolarDataMonitorBase(DataMonitorBase):
    """Solar Data Monitor Base Class"""

    def __init__(self):
        DataMonitorBase.__init__(self)

        self.location = self.directory.connect("location")
        self.report_missing_location = True

    def in_timespan(self, now, transit, window, repeat_days):
        """Check if now is in time span"""

        now = now.datetime()

        transit_time = transit.datetime()
        day_of_year = int(transit_time.strftime("%j"))

        if repeat_days and day_of_year % repeat_days != 0:
            return False

        return transit_time - window / 2 <= now < transit_time + window / 2

    def check_window(self):
        """Check if currently in the sample window"""

        # pylint: disable=too-many-return-statements

        location = self.location.best()

        if not location:
            if self.report_missing_location:
                self.report_missing_location = False
                self.log.info("No GPS or Iridium position data...")
            return False

        self.report_missing_location = True

        now = ephem.now()

        station = ephem.Observer()
        station.lat = str(location["latitude"])
        station.long = str(location["longitude"])
        station.date = now

        self.log.debug("station: %s", station)

        sun = ephem.Sun()
        sun.compute(station)
        solar_angle = float(sun.alt) * 180 / ephem.pi

        station.date = now
        next_transit = station.next_transit(sun)

        station.date = now
        prev_transit = station.previous_transit(sun)

        self.log.debug("  prev transit: %s", prev_transit)
        self.log.debug("  next transit: %s", next_transit)
        self.log.debug("  sun angle: %s", solar_angle)

        schedule = self.cur_schedule

        self.log.debug("  checking if in prev min")
        if self.in_timespan(
            now, prev_transit, schedule.window_min, schedule.repeat_days
        ):
            self.log.debug("    yes - turn on")
            return True

        self.log.debug("  checking if in next min")
        if self.in_timespan(
            now, next_transit, schedule.window_min, schedule.repeat_days
        ):
            self.log.debug("    yes - turn on")
            return True

        if schedule.min_solar_angle is not None:
            self.log.debug("  checking solar angle")
            if solar_angle < schedule.min_solar_angle:
                self.log.debug("    sun too low - turn off")
                return False

        if schedule.max_solar_angle is not None:
            if solar_angle >= schedule.max_solar_angle:
                self.log.debug("    sun too high - turn off")
                return False

        if schedule.window_max is None:
            return True

        self.log.debug("  checking if in prev window")
        if self.in_timespan(
            now, prev_transit, schedule.window_max, schedule.repeat_days
        ):
            self.log.debug("    yes - turn on")
            return True

        self.log.debug("  checking if in next window")
        if self.in_timespan(
            now, next_transit, schedule.window_max, schedule.repeat_days
        ):
            self.log.debug("    yes - turn on")
            return True

        self.log.debug("  failed to match any criteria")

        return False


class SolarDataMonitorComponent(SolarDataMonitorBase, ConfigComponent):
    """Solar Data Montior Component"""

    def __init__(self, *pos, **kw):
        ConfigComponent.__init__(self, "monitor", *pos, **kw)
        SolarDataMonitorBase.__init__(self)


class SolarDataMonitor(SolarDataMonitorBase, ProcessClient):
    """Solar Data Monitor"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)
        SolarDataMonitorBase.__init__(self)

    def main(self):
        """Main application loop"""

        for _step in self.step():
            if not self.wait(self.schedule_rate):
                break


if __name__ == "__main__":
    SolarDataMonitor(sys.argv).run()
