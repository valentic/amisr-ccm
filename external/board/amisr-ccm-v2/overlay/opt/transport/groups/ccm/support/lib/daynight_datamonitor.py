#!/usr/bin/env python
"""Day/Night Data Monitor"""

##########################################################################
#
#   Day/Night Data Monitor
#
#   A DataMonitor object with a schedule driven by the
#   location of the sun. We use the current GPS location
#   to compute solar local noon and operate within a
#   window around it.
#
#   2011-08-17  Todd Valentic
#               Initial implementation.
#               Based on SolarDataMonitor
#
#   2012-08-23  Todd Valentic
#               Differentiate between None and 0 in solar
#                   angle check.
#               Check for window_max is None
#
#   2011-08-26  Todd Valentic
#               Invalidate next_sample_time on schedule change
#
#   2012-03-04  Todd Valentic
#               Use DataMonitorMixin and create component
#
#   2021-04-11  Todd Valentic
#               Use DataMonitor cache methods
#
#   2021-06-30  Todd Valentic
#               Use location service
#
##########################################################################

import sys
import ephem

from datatransport import ProcessClient
from datatransport import ConfigComponent

from datamonitor import DataMonitorBase


class DayNightDataMonitorBase(DataMonitorBase):
    """DayNight Data Monitor Base Class"""

    def __init__(self):
        DataMonitorBase.__init__(self)

        self.report_missing_gps = True
        self.report_state = None

        self.location = self.directory.connect("location")

    def when_on(self):
        """On handler"""

        schedule = self.cur_schedule

        # Swap schedules based on solar angle

        rate = schedule.get_rate("sample.rate", 60)

        self.log.debug("dumping schedule (%s)", schedule.name)
        for option in schedule.options():
            self.log.debug("  %s: %s", option, schedule.get(option))

        if self.sun_up():
            rate = schedule.get_rate("day.sample.rate", rate)
            state = "day"

        else:
            rate = schedule.get_rate("night.sample.rate", rate)
            state = "night"

        self.cur_schedule.sample_rate = rate

        if self.report_state != state:
            self.log.info("State change: %s -> %s", self.report_state, state)
            if self.report_state:
                self.next_sample_time = None
            self.report_state = state

        DataMonitorBase.when_on(self)

    def in_timespan(self, now, transit, window, repeat_days):
        """Check if now is in time span"""

        now = now.datetime()

        transit_time = transit.datetime()
        day_of_year = int(transit_time.strftime("%j"))

        if repeat_days and day_of_year % repeat_days != 0:
            return False

        return transit_time - window / 2 <= now < transit_time + window / 2

    def sun_up(self):
        """Check if the sun is up"""

        # pylint: disable=too-many-return-statements

        location = self.location.best()

        if not location:
            if self.report_missing_gps:
                self.report_missing_gps = False
                self.log.info("No GPS or Iridium position data...")
            return False

        self.report_missing_gps = True

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
        if self.in_timespan(now, prev_transit, schedule.window_min, schedule.repeat_days):
            self.log.debug("    yes - turn on")
            return True

        self.log.debug("  checking if in next min")
        if self.in_timespan(now, next_transit, schedule.window_min, schedule.repeat_days):
            self.log.debug("    yes - turn on")
            return True

        if schedule.min_solar_angle is not None:
            self.log.debug("  checking min solar angle")
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
        if self.in_timespan(now, prev_transit, schedule.window_max, schedule.repeat_days):
            self.log.debug("    yes - turn on")
            return True

        self.log.debug("  checking if in next window")
        if self.in_timespan(now, next_transit, schedule.window_max, schedule.repeat_days):
            self.log.debug("    yes - turn on")
            return True

        self.log.debug("  failed to match any criteria")

        return False


class DayNightDataMonitorComponent(DayNightDataMonitorBase, ConfigComponent):
    """DayNight Data Monitor Component"""

    def __init__(self, *pos, **kw):
        ConfigComponent.__init__(self, "monitor", *pos, **kw)
        DayNightDataMonitorBase.__init__(self)


class DayNightDataMonitor(DayNightDataMonitorBase, ProcessClient):
    """DayNight Data Monitor"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)
        DayNightDataMonitorBase.__init__(self)

    def main(self):
        """Main application loop"""

        for _step in self.step():
            if not self.wait(self.schedule_rate)
                break


if __name__ == "__main__":
    DayNightDataMonitor(sys.argv).run()
