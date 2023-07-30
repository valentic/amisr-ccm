#!/usr/bin/env python3
"""Data Monitor"""

##########################################################################
#
#   Base class for data monitoring applications.
#
#   States:
#
#                       ----------------
#                      /  S  S  S  S  S \
#      |---------------                  ------------|
#      1      2        3        4       5            6
#
#      1 - startup
#      2 - when_off
#      3 - going_off_to_on
#      4 - when_on
#      5 - going_on_to_off
#      6 - shutdown
#
#      S - sample
#
#   In state 4 (on), we periodically sample at S.
#
#
#   2009-09-01  Todd Valentic
#               Initial implementation. Based on Imnavait Creek.
#
#   2009-10-30  Todd Valentic
#               Add output.rate support.
#               Renamed saveBinary -> save_data
#
#   2009-11-04  Todd Valentic
#               Add sample.offset
#               Add startup() and shutdown()
#               Add resource management
#
#   2009-11-05  Todd Valentic
#               Add scheduler and states
#
#   2009-11-06  Todd Valentic
#               Allow multiple resources in add/free
#
#   2009-11-11  Todd Valentic
#               Add setResources/clearResources. Clients should
#                   use these instead of directly calling allocate()
#
#   2009-11-18  Todd Valentic
#               Fix allocation bug in default shutdown()
#
#   2010-01-22  Todd Valentic
#               Add run_script() to consolidate script exec
#               Add get_status()
#
#   2010-03-17  Todd Valentic
#               Split off resource management into ResourceMixin
#               Add reloadable schedules
#
#   2010-04-29  Todd Valentic
#               Add schedule enabled check
#
#   2013-03-04  Todd Valentic
#               Split DataMonitor core into mixin
#
#   2013-05-14  Todd Valentic
#               Make sure to only grab the current instrument
#                   files in compress_filess()
#
#   2017-10-16  Todd Valentic
#               Add compression parameter - sometimes we don't
#                   want to compress small binary files.
#
#   2019-04-24  Todd Valentic
#               Add output file flush and fsync when writing
#                   to make writes more robust.
#
#   2019-04-29  Todd Valentic
#               Make status service configurable
#
#   2019-06-10  Todd Valentic
#               Include robust cache connection. A lot of derived
#                   clients use the cache, which at one point
#                   stopped and became a single point of failure.
#                   We include try..except protection and report
#                   errors here.
#
#   2019-07-22  Todd Valentic
#               Add output_enabled (default True)
#               Check if output path needs to be created
#
#   2021-04-07  Todd Valentic
#               Typo calling status_method
#               Change test for valid data from truth to None
#               Add list_cache()
#
#   2021-07-14  Todd Valentic
#               Use time at sample start for file timestamp
#
#   2022-05-02  Todd Valentic
#               Add sampleTime get/set
#
#   2023-06-16  Todd Valentic
#               Updated to transport3 / python3
#               Retain camelCase method names
#               Merge ResourceMixin back into DataMonitor
#
#   2023-07-07  Todd Valentic
#               Add get_state. 
#               Assume get_status() returns dict (json) 
#
##########################################################################

import bz2
import datetime
import functools
import os
import stat
import subprocess
import sys
import time

from pathlib import Path

from datatransport import ProcessClient
from datatransport import Root, Directory
from datatransport import ConfigComponent
import sapphire_config as sapphire

import schedule

# pylint: disable=too-many-public-methods
# pylint: disable=broad-exception-caught


class DataMonitorBase(Root):
    """Data Monitor base"""

    def __init__(self):
        Root.__init__(self)

        self.directory = Directory(self)
        self.instrument = self.config.get("instrument.name")

        if not self.instrument:
            self.abort("No instrument.name defined")

        self.resource_manager = self.directory.connect("resources")
        self.resources = {}

        status_service = self.config.get("status.service", "sbcctl")
        status_method = self.config.get("status.method", "status")

        self.status_service = self.directory.connect(status_service)
        self.status_method = getattr(self.status_service, status_method)

        self.cache = self.directory.connect("cache")
        self.schedules = schedule.ScheduleManager(self.log)
        self.cur_schedule = None
        self.on = False
        self._sample_time = None

        self.output_enabled = self.config.get_boolean("output.enabled", True)
        self.output_rate = self.config.get_timedelta("output.rate")
        self.output_path = self.config.get_path("output.path", "data-%Y%m%d-%H%M%S.dat")
        self.compress = self.config.get_boolean("output.compress", True)
        self.script_path = self.config.get("scripts")
        self.schedule_rate = self.config.get_rate("schedule.rate", 60)
        self.schedule_files = self.config.get_list("schedule.files")
        self.window_flag = self.config.get("force.flag.window")
        self.sample_flag = self.config.get("force.flag.sample")

        if self.output_rate:
            self.interval = self.output_rate.total_seconds()

        self.schedules.reload(self.schedule_files)

    # Resource management ################################################

    def _allocate(self):
        """Allocate resources with the resource manager"""

        values = list(self.resources.values())
        self.log.info("allocating resources: %s", values)
        self.resource_manager.allocate(self.instrument, values)

    def set_resources(self, *args):
        """Set a new resource list"""

        self.resources = {}

        for resource in args:
            name = resource.split("=")[0]
            self.resources[name] = resource

        self._allocate()

    def clear_resources(self):
        """Clear the resource list"""

        self.resources = {}
        self._allocate()

    def add_resource(self, *args):
        """Add a resource to the resource list"""

        for resource in args:
            name = resource.split("=")[0]
            self.resources[name] = resource

        self._allocate()

    def free_resource(self, *args):
        """Remove a resource from the resource list"""

        for resource in args:
            name = resource.split("=")[0]
            if name in self.resources:
                del self.resources[name]

        self._allocate()

    # System status ######################################################

    def get_status(self):
        """Get current status"""

        try:
            return self.status_method()
        except xmlrpc.client.Error as e: 
            self.log.error("Failed to get status: %s", e)

        return {} 

    def get_state(self, *keys, status=None):

        if not status:
            status = self.get_status()

        try:
            state = functools.reduce(dict.get, keys, status)
        except TypeError:
            state = None

        return state

    # Cache management ###################################################

    def put_cache(self, key, value):
        """Put value into cache"""

        try:
            return self.cache.put(key, value)
        except Exception:
            self.log.exception("Failed to set cache")
            return False

    def get_cache(self, key):
        """Get value from cache"""

        try:
            # server not configured for None yet
            # return self.cache_service.get_or_default(key,None)
            return self.cache.get(key)
        except Exception:
            self.log.error("No cache value for %s", key)
            return None

    def list_cache(self):
        """List cache keys"""

        try:
            return self.cache.list()
        except Exception:
            return []

    # Misc utilities #####################################################

    def run_script(self, basename, timeout=None):
        """Run script"""

        script = os.path.join(self.script_path, basename)

        if timeout:
            script = f"/usr/bin/timeout -t {timeout} {script}"

        self.log.info("Running %s", script)
        process = subprocess.run(
            script, capture_output=True, check=False, cwd=self.script_path
        )

        if process.returncode != 0:
            self.log.error("Problem running script")
            self.log.error("   script: %s", script)
            self.log.error("   status: %s", process.returncode)
            self.log.error("   stdout: %s", process.stdout)
            self.log.error("   stderr: %s", process.stderr)

            return False

        return True

    # Lifetime management #################################################

    def get_interval(self, timestamp):
        """Compute the interval containing timestamp"""

        if self.output_rate:
            return int(timestamp / self.interval) * self.interval

        return timestamp

    def sample(self):
        """Sample handler"""

        # Filled in by child class, returns data to be written
        return None

    def write(self, output, timestamp, data):
        """Write output handler"""
        # pylint: disable=unused-argument

        # Usually supplied by child class. Default is to just write.
        output.write(data)

    def startup(self):
        """Startup state"""
        # Filled in by child class

    def shutdown(self):
        """Shutdown state"""

        # Filled in by child class - default free all resources
        self.clear_resources()

    def when_off(self):
        """Off state"""

        # Filled in by child class

    def going_off_to_on(self):
        """Going from off to on state"""

        # Filled in by child class
        self.on = True

    def compute_next_sample_time(self, now):
        """Compute next sample time from schedule"""

        if not self.cur_schedule:
            return None

        return now + self.cur_schedule.sample_rate.nexttime(now) 

    def when_on(self):
        """On state"""

        now = self.now().replace(microsecond=0)

        if not self.next_sample_time:
            self.next_sample_time = self.compute_next_sample_time(now)

        if self.check_flag(self.sample_flag):
            self.next_sample_time = now 
            try:
                os.remove(self.sample_flag)
            except OSError as e:
                self.log.exception("Failed to remove sample flag: %s", e)

        self.log.debug("Next sample time: %s", self.next_sample_time)

        if self.next_sample_time and now >= self.next_sample_time:
            self.sampling_cycle()
            self.next_sample_time = self.compute_next_sample_time(now)

    def going_on_to_off(self):
        """Going from on to off state"""

        # Filled in by child class
        self.on = False

    def is_on(self):
        """Monitored device is on"""

        # Filled in by child class
        return self.on

    def is_off(self):
        """Monitored device is off"""

        return not self.is_on()

    def check_flag(self, filename):
        """Check if flag file is set"""

        return filename and os.path.exists(filename)

    def check_window(self):
        """Check if we are in sampling window"""

        # Derived classes extend this for more interesting logic.
        return self.cur_schedule.in_window()

    def scheduler(self):
        """Schedule points"""

        self.next_sample_time = None

        while True:
            yield True

            if self.schedules.reload(self.schedule_files):
                self.next_sample_time = None

            now = self.now().replace(microsecond=0)

            self.cur_schedule = self.schedules.match(now)

            if self.cur_schedule:
                in_window = self.cur_schedule.enabled and self.check_window()
            else:
                in_window = False

            if self.check_flag(self.window_flag):
                in_window = True

            on = self.is_on()

            if not on and not in_window:
                self.when_off()
                continue

            if not on and in_window:
                self.log.info("Going on")
                self.going_off_to_on()
                if self.cur_schedule and self.cur_schedule.sample_rate.at_start:
                    self.next_sample_time = now 
                    self.when_on()
                self.next_sample_time = self.compute_next_sample_time(now)
                continue

            if on and in_window:
                self.when_on()
                continue

            if on and not in_window:
                self.log.info("Going off")
                self.going_on_to_off()
                continue

    def get_data_time(self, data):
        """Can be filled in by child classes for a time derived by the data."""
        # pylint: disable=unused-argument

        return time.time()

    def get_sample_time(self):
        """Get current sample time"""

        # Unix timestamp
        return self._sample_time

    def set_sample_time(self, timestamp):
        """Set current sample time"""

        if isinstance(timestamp, datetime.datetime):
            timestamp = time.mktime(timestamp.timetuple())
        self._sample_time = timestamp

    def sampling_cycle(self):
        """Sample step"""

        # pylint: disable=assignment-from-none

        try:
            self.set_sample_time(time.time())
            data = self.sample()
            if data is not None and self.output_enabled:
                self.save_data(self.get_sample_time(), data)
                self.compress_files()
        except Exception:
            self.log.exception("Failed to collect data")

    def step(self):
        """Application generator loop"""

        try:
            self.startup()
            startup_ok = True
        except Exception:
            self.log.exception("Failed to startup")
            startup_ok = False

        if startup_ok:
            try:
                for _k in self.scheduler():
                    yield 1
            except GeneratorExit:
                self.log.info("generator exiting")
            except Exception:
                self.log.exception("Failed in schedule")

        try:
            self.shutdown()
        except Exception:
            self.log.exception("Failed to shutdown")

    def save_data(self, timestamp, buffer):
        """Write data into current output file"""

        interval = self.get_interval(timestamp)
        dt = datetime.datetime.utcfromtimestamp(interval)
        localfile = Path(dt.strftime(str(self.output_path.name)))

        with localfile.open("ab") as output:
            self.write(output, timestamp, buffer)
            output.flush()
            os.fsync(output.fileno())

        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
        localfile.chmod(mode)

        self.log.debug(str(localfile))

    def compress_files(self):
        """Move and optionally compress output files to spool"""

        ext = self.output_path.suffix
        prefix = self.output_path.name.split("-")[0]
        filenames = sorted(Path(".").glob(f"{prefix}*{ext}"))

        if self.output_rate:
            filenames = filenames[:-1]

        for filename in filenames:
            data = filename.read_bytes()

            outputname = self.output_path.parent / filename.name

            if self.compress:
                zdata = bz2.compress(data)
                outputname = outputname.with_suffix(ext + ".bz2")
                action = "compressing"
            else:
                zdata = data
                action = "copying"

            outputname.parent.mkdir(parents=True, exist_ok=True)

            with outputname.open("wb") as output:
                output.write(zdata)
                output.flush()
                os.fsync(output.fileno())

            self.log.info("%s %s: %d -> %d", action, filename, len(data), len(zdata))

            filename.unlink()


class DataMonitorComponent(DataMonitorBase, ConfigComponent):
    """Data Monitor Component"""

    def __init__(self, *pos, **kw):
        ConfigComponent.__init__(self, "monitor", *pos, **kw)
        DataMonitorBase.__init__(self)


class DataMonitor(DataMonitorBase, ProcessClient):
    """Data Monitor Class"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)
        DataMonitorBase.__init__(self)

    def main(self):
        """Main application loop"""

        for _step in self.step():
            if not self.wait(self.schedule_rate):
                break


if __name__ == "__main__":
    DataMonitor(sys.argv).run()
