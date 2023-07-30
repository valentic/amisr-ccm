#!/usr/bin/env python3
"""Night Data Monitor"""

##########################################################################
#
#   Night Data Monitor
#
#   A DataMonitor object with a schedule driven by the
#   location of the sun. We use the current GPS location
#   to compute solar elevation angle and turn on when
#   the sun is below a given angle.
#
#   2021-06-10  Todd Valentic
#               Initial implementation. Based on SolarDataMonitor
#
#   2021-06-30  Todd Valentic
#               Use location service
#
#   2021-07-23  Todd Valentic
#               Base window selection on rising/setting times
#               Add warmup time parameter
#
#   2023-07-05  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import sys
import pytz

import ephem

from datatransport import ProcessClient
from datatransport import ConfigComponent

from datamonitor import DataMonitorBase


class NightDataMonitorBase(DataMonitorBase):
    """Night Data Monitor Base Class"""

    def __init__(self):
        DataMonitorBase.__init__(self)

        self.report_missing_location = True
        self.location = self.directory.connect("location")

    def check_window(self):
        """check if in window"""
        # pylint: disable=too-many-return-statements

        schedule = self.cur_schedule
        location = self.location.best()

        if not location:
            # Report missing data once so we don't spam the log
            if self.report_missing_location:
                self.report_missing_location = False
                self.log.info("No location data.")
            return False

        # We have a good position, reset flag
        self.report_missing_location = True

        if schedule.min_solar_angle is None:
            # Nothing to do
            return False

        offset_time = schedule.get_timedelta("start.offset")

        sun = ephem.Sun()

        station = ephem.Observer()
        station.lat = str(location["latitude"])
        station.lon = str(location["longitude"])
        station.date = ephem.now()
        station.horizon = str(schedule.min_solar_angle)

        self.log.debug("Station: %s", station)

        # If the sun is already set, then turn on

        sun.compute(station)
        solar_angle = float(sun.alt) * 180 / ephem.pi

        self.log.debug("Checking solar angle: %s", solar_angle)

        if solar_angle <= schedule.min_solar_angle:
            self.log.debug("  - sun is below min elevation. Turn on")
            return True

        # If we are approaching sunset, check the offset time

        if offset_time is not None:
            self.log.debug("Checking sunset time with offset %s", offset_time)

            try:
                next_setting = station.next_setting(sun, use_center=True)
                self.log.debug("  next setting at %s", next_setting)
            except ephem.AlwaysUpError:
                self.log.debug("  sun is always up. Turn off.")
                return False
            except ephem.NeverUpError:
                self.log.debug("  sun is never up. Turn on.")
                return True

            next_setting = next_setting.datetime().replace(tzinfo=pytz.utc)

            if self.currentTime() >= (next_setting - offset_time):
                self.log.debug("  in pre-sunset time window. Turn on")
                return True

        self.log.debug("Sun is above min elevation - turn off")

        return False


class NightDataMonitorComponent(NightDataMonitorBase, ConfigComponent):
    """Night Data Monitor Component"""

    def __init__(self, *pos, **kw):
        ConfigComponent.__init__(self, "monitor", *pos, **kw)
        NightDataMonitorBase.__init__(self)


class NightDataMonitor(NightDataMonitorBase, ProcessClient):
    """Night Data Monitor"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)
        NightDataMonitorBase.__init__(self)

    def main(self):
        """Main application loop"""

        for _step in self.step():
            if not self.wait(self.schedule_rate):
                break


if __name__ == "__main__":
    NightDataMonitor(sys.argv).run()
