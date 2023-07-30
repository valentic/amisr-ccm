#!/usr/bin/env python3
"""Resource Manager Service"""

##########################################################################
#
#   Resource Manager Service
#
#   Management of onboard resources
#
#   2009-08-21  Todd Valentic
#               Initial implementation.
#
#   2009-10-21  Todd Valentic
#               First release version.
#
#   2010-01-25  Todd Valentic
#               Add background states and delay
#
#   2010-03-16  Todd Valentic
#               Remove need to explicitly list users
#
#   2021-07-12  Todd Valentic
#               Run reconcile in background
#
#   2023-06-05  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import functools
import subprocess
import sys
import threading

from datatransport import ProcessClient
from datatransport import XMLRPCServer
from datatransport import Directory
from datatransport import AccessMixin
from datatransport import ConfigComponent
from datatransport.utilities import PatternTemplate

# pylint: disable=bare-except


class ResourceState(ConfigComponent):
    """Resource State"""

    def __init__(self, name, config, parent, **kw):
        ConfigComponent.__init__(self, "state", name, config, parent, **kw)

        self.command = self.config.get("command")
        self.service = self.config.get("service")
        self.values = self.config.get_list("values", self.config.get("value", ""))


class Resource(ConfigComponent):
    """Resource Component"""

    def __init__(self, name, config, parent, **kw):
        ConfigComponent.__init__(self, "resource", name, config, parent, **kw)

        self.order = self.config.get_list("states")
        self.states = self.config.get_components("states", factory=ResourceState)
        self.params = set(self.config.get_list("params"))
        self.reset = self.config.get("reset.state", self.order[0])
        self.default = self.config.get("default.state", self.order[-1])
        self.keys = self.config.get_list("status.key")

        if not self.params:
            self.params.add("")

        self.replace_param = PatternTemplate("param")

        if self.reset not in self.order:
            raise ValueError(f"Unknown reset.state ({self.reset}) for {name}")

        if self.default not in self.order:
            raise ValueError(f"Unknown default.state ({self.reset}) for {name}")

        self.log.info("Resource %s:", name)

        for key in self.order:
            state = self.states[key]
            if state.command:
                self.log.info("  %s: [C] %s", state.name, state.command)
            if state.service:
                self.log.info("  %s: [S] %s", state.name, state.service)

    def get_state(self, status, param):
        """Get state of the resource from status"""

        keys = [self.replace_param(key, param) for key in self.keys]

        try:
            value = functools.reduce(dict.get, keys, status)
        except TypeError:
            value = None

        for state in self.states.values():
            if value in state.values:
                return state.name

        raise ValueError(f"Unknown state for {self.name} ({value})")

    def reset_state(self):
        """Rsset state"""

        return (self.params, self.reset)

    def rollup(self, entries):
        """Rollup"""

        paramsdict = {}

        for param in self.params:
            paramsdict[param] = set()

        for entryparams, state in entries.values():
            for param in entryparams:
                paramsdict[param].add(state)

        result = {}

        for param, states in paramsdict.items():
            result[param] = self.select_state(states)

        return result

    def select_state(self, states):
        """Select state"""

        for state in reversed(self.order):
            if state in states:
                return state

        return self.default

    def reconcile(self, status, entry):
        """Reconcile"""

        for param, next_state in entry.items():
            try:
                cur_state = self.get_state(status, param)
            except:
                self.log.exception("Failed to get status for %s", self.name)
                continue

            if cur_state != next_state:
                if param:
                    msg = f"[{param}] {cur_state} -> {next_state}"
                else:
                    msg = f"{cur_state} -> {next_state}"
                self.log.info(msg)
                self.run_command(self.states[next_state].command, param)
                self.run_service(self.states[next_state].service, param)

    def run_command(self, cmd, param):
        """Run a shell command"""

        if not cmd:
            return

        cmd = self.replace_param(cmd, param)
        subprocess.getstatusoutput(cmd)

    def run_service(self, cmd, param):
        """Call a service"""

        if not cmd:
            return

        cmd = self.replace_param(cmd, param).split()
        service_name, function, args = cmd[0], cmd[1], cmd[2:]

        self.log.debug(f"{service_name}: {function} {args}")

        service = self.parent.connect(service_name)
        getattr(service, function)(*args)


class ScoreBoard(AccessMixin):
    """ScoreBoard"""

    def __init__(self, parent, resources):
        AccessMixin.__init__(self, parent)

        self.users = set()
        self.resources = resources

        self.reset()

    def reset(self):
        """Reset state"""

        self.map = {}

        for resource in self.resources.values():
            self.map[resource.name] = {}

    def allocate(self, user, resource_list):
        """Allocate resources"""

        if user not in self.users:
            for resource in self.resources.values():
                self.map[resource.name][user] = resource.reset_state()
                self.users.add(user)

        requested = {}
        for entry in resource_list:
            entry = entry.strip()

            if "=" in entry:
                resource, state = entry.rsplit("=", 1)
            else:
                resource, state = entry, None

            if "[" in resource:
                resource, params = resource.split("[", 1)
                params = params.replace("]", "")
                params = {p.strip() for p in params.split(",")}
            else:
                params = set([""])

            if resource not in self.resources:
                self.log.error("Unknown resource request: %s", entry)
                continue

            requested[resource] = (params, state)

        for resource in set(self.resources).difference(requested):
            self.map[resource][user] = self.resources[resource].reset_state()

        for resource, state in requested.items():
            self.map[resource][user] = state

    def rollup(self):
        """Compute next state"""

        next_state = {}

        for resource, users in self.map.items():
            next_state[resource] = self.resources[resource].rollup(users)

        return next_state


class ResourceMonitor(ProcessClient):
    """Resource Monitor"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        pollrate = self.config.get_rate("pollrate", 10)
        self.reconcile_lock = threading.Lock()

        self.xmlserver = XMLRPCServer(self, callback=self.reconcile, timeout=pollrate)
        self.connect = Directory(self)

        self.xmlserver.register_function(self.status)
        self.xmlserver.register_function(self.allocate)

        self.resources = self.config.get_components("resources", factory=Resource)
        self.status_command = self.config.get("status.command")
        self.status_service = self.config.get("status.service")
        self.ready_service = self.config.get("status.ready")

        self.scoreboard = ScoreBoard(self, self.resources)

    def status(self):
        """Return current scoreboard state"""

        return str(self.scoreboard.map)

    def allocate(self, monitor, resources):
        """Allocate resources"""

        self.log.info("allocation request from %s: %s", monitor, resources)
        try:
            self.scoreboard.allocate(monitor, resources)
        except:
            self.log.exception("Problem parsing resource request")
            raise

        self.reconcile()

        return True

    def reconcile(self):
        """Wrapper to call reconcile step"""

        # pylint: disable=consider-using-with

        if not self.reconcile_lock.acquire(blocking=False):
            self.log.debug("reconcile is locked., skipping")
            return

        try:
            self._reconcile()
        except:
            self.log.exception("Problem reconciling system state")
            raise
        finally:
            self.reconcile_lock.release()

    def _reconcile(self):
        """Reconcile differences between expected and actual system state"""

        self.log.debug("Reconciling system state")

        if self.is_stopped():
            return

        try:
            status = self.get_current_status()
        except:
            self.log.exception("Failed to get current system status")
            return

        next_state = self.scoreboard.rollup()

        for resource, users in next_state.items():
            self.resources[resource].reconcile(status, users)

        self.log.debug("  finished")

    def get_current_status(self):
        """Get the current system status"""

        if self.status_command:
            return self.run_command(self.status_command)

        if self.status_service:
            return self.run_service(self.status_service)

        raise IOError("No status service/command given")

    def run_command(self, cmd):
        """Run a shell command"""

        status, output = subprocess.getstatusoutput(cmd)

        if status != 0:
            self.log.error("Failed to run status command")
            self.log.error("  command: %s", cmd)
            self.log.error("  status:  %s", status)
            self.log.error("  output:  %s", output)
            raise IOError()

        return output

    def run_service(self, cmd):
        """Call a network service"""

        cmd = cmd.split()
        service_name, function, args = cmd[0], cmd[1], cmd[2:]

        service = self.connect(service_name)
        return getattr(service, function)(*args)

    def main(self):
        """Main application"""

        ready = False

        self.log.info("Waiting for status service to be ready")

        while self.wait(1) and not ready:
            try:
                ready = self.run_service(self.ready_service)
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.log.error("Waiting for ready: %s", e)

        if not ready:
            return

        self.log.info("Status service is ready")

        self.allocate("background", self.config.get_list("background.state.start"))
        self.xmlserver.main()
        self.allocate("background", self.config.get_list("background.state.stop"))


if __name__ == "__main__":
    ResourceMonitor(sys.argv).run()
