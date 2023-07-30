#!/usr/bin/env python3
"""Uplink Monitor"""

##########################################################################
#
#   Uplink Monitor
#
#   Control and monitor the uplink connection (usually the Starlink).
#
#   2023-07-15  Todd Valentic
#               Initial implementation
#
##########################################################################

import enum
import sys

from datamonitor import DataMonitor


class State(enum.Enum):
    """Link States"""

    UNKNOWN = (0,)
    ONLINE = (1,)
    OFFLINE = 2


class UplinkMonitor(DataMonitor):
    """Uplink Data Monitor"""

    def __init__(self, argv):
        DataMonitor.__init__(self, argv)

        self.checkin_flag = self.config.get_path("checkin.flag")

        self.device = self.config.get("connection.device", "starlink")
        self.on_state = self.config.get("connection.device.state.on", "on")
        self.off_state = self.config.get("connection.device.state.off", "off")

        self.device_on = f"{self.device}={self.on_state}"
        self.device_off = f"{self.device}={self.off_state}"

        self.timeout = self.config.get_timedelta("connection.timeout", "15m")
        self.backoff_factor = self.config.get_int("connection.backoff.factor", 2)
        self.backoff_step = self.config.get_timedelta("connection.backoff.step", "15m")
        self.backoff_limit = self.config.get_timedelta("connection.backoff.limit", "1h")

        self.report_rate = self.config.get_rate("report.rate", "15m")

        self.state = None
        self.update_state(State.UNKNOWN)

        self.log.info("Ready to start")

    def update_state(self, curstate):
        """Update current state"""

        now = self.now().replace(microsecond=0)

        if self.state != curstate:
            self.state = curstate
            self.count = 0
            self.start_time = now
            self.deadline = now
            self.report_deadline = now

        self.elapsed = now - self.start_time

        status = {
            "state": self.state.name,
            "elapsed": self.elapsed.total_seconds(),
            "start": self.start_time,
            "count": self.count,
            "deadline": self.deadline,
        }

        self.put_cache(self.instrument, status)

    def going_off_to_on(self):
        """Off to on handler"""

        self.set_resources(self.device_on)
        self.update_state(State.UNKNOWN)

    def going_on_to_off(self):
        """On to off handler"""

        self.clear_resources()
        self.update_state(State.UNKNOWN)

    def is_on(self):
        """Test if uplink device is on"""

        self.on = self.get_state("device", self.device) == "on"
        return self.on

    def power_cycle(self):
        """Power cycle uplink device"""

        self.free_resource(self.device_off)
        self.wait(5)
        self.add_resource(self.device_on)

    def report(self, *pos, **kw):
        """Rate limited log reporting"""

        now = self.now()

        if now > self.report_deadline:
            self.log.info(*pos, **kw)
            self.report_deadline = now + self.report_rate.nexttime(now)

    def sample(self):
        """Sample handler"""

        # Use the tincan checkin flag for connection status

        now = self.now()

        if self.checkin_flag.exists():
            checkin_time = self.checkin_flag.stat().st_mtime
            delta_t = now.timestamp() - checkin_time
            active = delta_t < self.timeout.total_seconds()
        else:
            active = False

        if active:
            self.update_state(State.ONLINE)
            self.report("[ UP ] Uptime: %s", self.elapsed)

        elif now < self.deadline:
            self.update_state(State.OFFLINE)
            self.report("[DOWN] Downtime: %s", self.elapsed)

        else:
            self.update_state(State.OFFLINE)
            self.log.info("[DOWN] Downtime: %s", self.elapsed)
            self.log.info("[DOWN]   - power cycling %s", self.device)

            self.power_cycle()

            backoff = pow(self.backoff_factor, self.count) * self.backoff_step

            if backoff > self.backoff_limit:
                backoff = self.backoff_limit
            else:
                self.count += 1

            self.deadline = now.replace(microsecond=0) + backoff

            self.log.info("[DOWN]   - backoff %s", backoff)
            self.log.info("[DOWN]   - next deadline %s", self.deadline)


if __name__ == "__main__":
    UplinkMonitor(sys.argv).run()
