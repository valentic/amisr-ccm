#!/usr/bin/env python3
"""PDU Control Service"""

##########################################################################
#
#   PDU control service
#
#   This service is used to access the power distribution unit (PDU)
#   The heavy lifting is done through the pductl program.
#
#   2018-05-30  Todd Valentic
#               Initial implementation.
#
#   2018-06-12  Todd Valentic
#               Expand to handle multiple PDUs
#
#   2018-07-16  Todd Valentic
#               Add stages
#
#   2019-07-02  Todd Valentic
#               Support new PDU models (small payload)
#
#   2021-09-22  Todd Valentic
#               Add support for command retries
#
#   2023-07-20  Todd Valentic
#               Updated for transport3 / python3
#               Move start up staging into this service
#               Use snake_case for names
#
#   2023-10-06  Todd Valentic
#               Check for null commands
#
##########################################################################

import functools
import sys

from datatransport import ProcessClient
from datatransport import Directory
from datatransport import XMLRPCServer
from datatransport import ConfigComponent


# pylint: disable=bare-except


class State(ConfigComponent):
    """Rail State"""

    def __init__(self, name, config, parent):
        ConfigComponent.__init__(self, "state", name, config, parent)

        self.set_cmd = self.config.get_list("set")
        self.value = self.config.get("value")

        self.log.info("set: %s", self.set_cmd)
        self.log.info("value: %s", self.value)

    def __eq__(self, other):
        return other == self.value

    def as_dict(self):
        """Serialize as dictionary"""

        return {"value": self.value, "name": self.name}


class Stage(ConfigComponent):
    """Rail Stage"""

    def __init__(self, name, config, parent):
        ConfigComponent.__init__(self, "stage", name, config, parent)

        self.duration = self.config.get_timedelta("duration", 0)
        self.state = self.config.get("state", "on")
        self.call = parent.parent.call

        self.log.info("%s: %s", self.state, self.duration)

    def as_dict(self):
        """Serialize as dictionary"""

        return {
            "duration": self.duration.total_seconds(),
            "state": self.state,
            "name": self.name,
        }

    def startup(self):
        """Startup generator"""

        self.log.info(self.state)

        deadline = self.now() + self.duration
        rail = self.parent

        self.call(*rail.states[self.state].set_cmd)

        while self.now() < deadline:
            yield True


class Rail(ConfigComponent):
    """Rail Component"""

    def __init__(self, name, config, parent):
        ConfigComponent.__init__(self, "rail", name, config, parent)

        self.call = parent.call

        self.stages = self.config.get_components("stages", factory=Stage)
        self.states = self.config.get_components("states", factory=State)

        self.label = self.config.get("label", self.name)
        self.device = self.config.get("device", self.name)
        self.status_keys = self.config.get_list("status.key", self.name)

        self.enabled = True

        if not self.device:
            if not self.label:
                self.enabled = False
            else:
                self.device = self.label.lower().replace(" ", "_")

        if self.enabled:
            self.log.info(self.label)

    def as_dict(self):
        """Serialize as dictionary"""

        return {
            "label": self.label,
            "device": self.device,
            "enabled": self.enabled,
            "stages": [stage.as_dict() for stage in self.stages.values()],
            "states": [state.as_dict() for state in self.states.values()],
        }

    def get_state(self, status):
        """Get rail state from status"""

        try:
            value = functools.reduce(dict.get, self.status_keys, status)
        except TypeError:
            value = None

        for state in self.states.values():
            if state == value:
                return state.name

        return None

    def set_state(self, state):
        """Set rail state"""

        return self.call(*self.states[state].set_cmd)

    def startup(self):
        """Startup generator"""

        if not self.enabled:
            return

        self.log.debug("Starting rail")

        for stage in self.stages.values():
            for step in stage.startup():
                yield step

        self.log.debug("Rail is up")


class PDU(ConfigComponent):
    """PDU Component"""

    def __init__(self, name, config, parent):
        ConfigComponent.__init__(self, "pdu", name, config, parent)

        self.directory = parent.directory

        self.max_retries = self.config.get_int("retry.max", 3)
        self.retry_wait = self.config.get_timedelta("retry.wait", 2)
        self.rails = self.config.get_components("rails", factory=Rail)

        self.status_service = self.config.get_list("status.service")

    def startup(self):
        """Startup generator"""

        self.log.info("Starting rails")

        gens = [rail.startup() for rail in self.rails.values()]

        while gens and self.is_running():
            nextgens = []

            for gen in gens:
                try:
                    next(gen)
                    nextgens.append(gen)
                except StopIteration:
                    pass

            gens = nextgens

            yield True

        self.log.info("All rails are up")

    def call(self, *args):
        """Call service if defined"""

        if not args:
            return None

        return self.call_handler(*args)

    def call_handler(self, service, cmd, *args):
        """Execute command"""

        self.log.debug("%s %s", service, args)

        retry_count = 0

        while retry_count <= self.max_retries and self.is_running():
            svc = self.directory.connect(service)
            func = getattr(svc, cmd)
            try:
                return func(*args)
            except:
                self.log.exception("error for %s %s", service, cmd)
                retry_count += 1

            self.wait(self.retry_wait)

        raise IOError(f"Timeout running {service} {cmd}")

    def get_status(self):
        """Get status from source"""

        return self.call(*self.status_service)

    def get_state(self):
        """Return the state of the rails and devices"""

        status = self.get_status()

        results = {"rail": {}, "device": {}}

        for rail in self.rails.values():
            results["rail"][rail.name] = rail.get_state(status)
            results["device"][rail.device] = rail.get_state(status)

        return results

    def as_dict(self):
        """Serialize as dict"""

        rails = {}

        for key, rail in self.rails.items():
            rails[key] = rail.as_dict()

        return {"rails": rails}

    def set_rail(self, rail_name, state):
        """Set rail state"""

        if rail_name not in self.rails:
            msg = f"Attempt to set unknown rail {rail_name}"
            self.log.error(msg)
            raise KeyError(msg)

        self.rails[rail_name].set_state(state)

        return True

    def map_devices(self):
        """Map device name to rail"""

        return {r.device: r for r in self.rails.values()}


class Server(ProcessClient):
    """PDU Control Server"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.xmlserver = XMLRPCServer(self, callback=self.idle)
        self.directory = Directory(self)
        self.service_name = self.config.get("service.name")

        self.pdus = self.config.get_components("pdus", factory=PDU)
        self.ready = False

        self.xmlserver.register_function(self.get_status)
        self.xmlserver.register_function(self.get_state)
        self.xmlserver.register_function(self.set_rail)
        self.xmlserver.register_function(self.set_device)
        self.xmlserver.register_function(self.list)
        self.xmlserver.register_function(self.is_ready)

        self.cache = self.directory.connect("cache")

        self.devices = self.map_devices()

    def map_devices(self):
        """Map device names to corresponding pdu/rail"""

        devices = {}

        for pdu in self.pdus.values():
            devices.update(pdu.map_devices())

        return devices

    def get_state(self):
        """Return PDU rail states"""

        results = {}

        pdu_state = {}
        device_state = {}

        for pdu in self.pdus.values():
            state = pdu.get_state()
            pdu_state[pdu.name] = state["rail"]
            device_state.update(state["device"])

        results = {"pdu": pdu_state, "device": device_state}

        self.cache.put(f"{self.service_name}", results)

        return results

    def get_status(self):
        """Return PDU status"""

        results = {}

        for pdu in self.pdus.values():
            results[pdu.name] = pdu.get_status()

        self.cache.put(f"{self.service_name}.status", results)

        return results

    def set_rail(self, pdu_name, rail_name, state):
        """Set rail state"""

        if pdu_name not in self.pdus:
            msg = f"Unknown PDU {pdu_name}"
            self.log.error(msg)
            raise KeyError(f"Unknown PDU {pdu_name}")

        self.pdus[pdu_name].set_rail(rail_name, state)

        self.get_state()

        return True

    def set_device(self, device_name, state):
        """Set device state"""

        self.log.info("%s %s", device_name, state)
        self.devices[device_name].set_state(state)

        return True

    def list(self):
        """List PDU details"""

        results = {}

        for key, pdu in self.pdus.items():
            results[key] = pdu.as_dict()

        return results

    def is_ready(self):
        """Startup finished. Ready for operations"""

        return self.ready

    def startup(self):
        """Startup power rails"""

        gens = [pdu.startup() for pdu in self.pdus.values()]

        while gens and self.is_running():
            nextgens = []

            for gen in gens:
                try:
                    next(gen)
                    nextgens.append(gen)
                except StopIteration:
                    pass

            gens = nextgens

            yield False

        return len(gens) == 0

    def idle(self):
        """Idle handler. Step through startup"""

        if self.ready:
            return

        while self.is_running:
            try:
                next(self.startup_gen)
            except StopIteration:
                break

        self.ready = True

    def main(self):
        """Main application"""

        self.startup_gen = self.startup()
        self.xmlserver.main()


if __name__ == "__main__":
    Server(sys.argv).run()
