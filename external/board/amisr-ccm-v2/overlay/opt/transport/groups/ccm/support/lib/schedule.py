#!/usr/bin/env python3
"""Schedule Manager"""

##########################################################################
#
#   Schedule Manager
#
#   2010-01-21  Todd Valentic
#               Initial implementation
#
#   2010-03-17  Todd Valentic
#               Return None instead of exception if no
#                   matching schedule is found.
#
#               Add window start/stop/span and check
#
#   2010-03-18  Todd Valentic
#               Rework sample window to have rate/offset/span
#               Read schedule files one at a time in case one
#                   of them has errors (otherwise all were rejected).
#
#   2010-03-22  Todd Valentic
#               Make sure empty schedule list exists.
#
#   2010-04-29  Todd Valentic
#               Add enabled parameter
#               Make time comparisons in UTC
#
#   2011-04-02  Todd Valentic
#               Make schedule-specific config parameters available
#               Move getTimeSpan in to ExtendedConfigParser
#
#   2011-08-25  Todd Valentic
#               Add try..except around Schedule creation.
#               Default window_max to None
#
#   2023-06-16  Todd Valentic
#               Updates for transport3 / python3
#               Replace ExtendedConfigParser with sapphire.Parser
#
##########################################################################

import configparser
import datetime
import glob
import os
import pathlib
import time

import sapphire_config as sapphire
from dateutil import parser as dateparser
from dateutil.relativedelta import relativedelta

utc = datetime.timezone.utc


class Schedule:
    """Individual Schedule"""

    def __init__(self, name, config):
        self.name = name

        proxy = config[name]

        for method in dir(proxy):
            if method.startswith("get"):
                func = getattr(proxy, method)
                setattr(self, method, func)

        self.options = config.options(name)

        self.enabled = self.get_boolean("enabled", True)
        self.start_time = self.get("time.start")
        self.stop_time = self.get("time.stop")
        self.timespan = self.get_timespan("time.span")
        self.min_solar_angle = self.get_float("solarangle.min", -6)
        self.max_solar_angle = self.get_float("solarangle.max")
        self.repeat_days = self.get_int("repeat.days")
        self.priority = self.get_int("priority", 10)
        self.window_min = self.get_timedelta("window.min", 0)
        self.window_max = self.get_timedelta("window.max")
        self.sample_rate = self.get_rate("sample.rate", 60)
        self.window_rate = self.get_rate("window.rate")
        self.window_span = self.get_timedelta("window.span", 60)

    def match(self, target_time):
        """Schedule is active for target_time"""

        now = datetime.datetime.now()
        this_year = datetime.datetime(now.year, 1, 1)

        try:
            start_time = dateparser.parse(self.start_time, default=this_year)
            start_time = start_time.replace(tzinfo=utc)
        except (dateparser.ParserError, TypeError):
            start_time = None

        try:
            stop_time = dateparser.parse(self.stop_time, default=this_year)
            stop_time = stop_time.replace(tzinfo=utc)
        except (dateparser.ParserError, TypeError):
            stop_time = None

        if start_time and not stop_time and self.timespan:
            stop_time = start_time + self.timespan

        if start_time and stop_time:
            if stop_time < start_time:
                stop_time += relativedelta(years=1)

        if start_time and target_time < start_time:
            return False

        if stop_time and target_time >= stop_time:
            return False

        return True

    def in_window(self):
        """Currently in this schedule's window"""

        if not self.window_rate:
            return True

        now = time.time()
        period = self.window_rate.period.total_seconds()
        offset = self.window_rate.offset.total_seconds()
        span = self.window_span.total_seconds()

        interval = int(now / period) * period
        start_time = interval + offset
        stop_time = start_time + span

        return start_time <= now < stop_time


class ScheduleManager:
    """Manage a group of schedules"""

    def __init__(self, log):
        self.log = log
        self.filetimes = {}
        self.schedules = []

    def load(self, filenames):
        """Load schedule files"""

        self.log.info("Loading schedules:")

        self.schedules = []

        config = sapphire.Parser()

        for filename in sorted(filenames):
            try:
                config.read(filename)
            except configparser.ParsingError as e:
                self.log.error("Failed to read %s: %s", filename, e)

        for section in config.sections():
            try:
                schedule = Schedule(section, config)
                self.schedules.append(schedule)
            except Exception:  # pylint: disable=broad-exception-caught
                self.log.exception("Failed to create schedule %s")

        self.schedules.sort(reverse=True, key=lambda s: s.priority)

        for schedule in self.schedules:
            self.log.info("  - [%d] %s", schedule.priority, schedule.name)

    def reload(self, filespecs):
        """Reload schedule files"""

        filenames = []

        for filespec in filespecs:
            filenames.extend(glob.glob(filespec))

        reload = False

        newfiles = set(filenames).difference(self.filetimes)
        stalefiles = set(self.filetimes).difference(filenames)
        checkfiles = set(self.filetimes).intersection(filenames)

        if newfiles or stalefiles:
            reload = True

        curtimes = {}

        for filename in newfiles:
            curtimes[filename] = os.stat(filename).st_mtime

        for filename in checkfiles:
            mtime = os.stat(filename).st_mtime
            if mtime != self.filetimes[filename]:
                reload = True
            curtimes[filename] = mtime

        self.filetimes = curtimes

        if reload:
            self.load(filenames)

        return reload

    def match(self, target_time):
        """Find first schedule that is active for target_time"""

        for schedule in self.schedules:
            if schedule.match(target_time):
                return schedule

        return None
