#!/usr/bin/env python3
"""Meter Interface Service"""

##########################################################################
#
#   General service for accessing hardware meters.
#
#   2023-08-02  Todd Valentic
#               Initial implementation
#
#   2023-08-09  Todd Valentic
#               Check if host is online
#               Add meter type parameter
#
#   2023-08-24  Todd Valentic
#               Make sure network cache is present
#
#   2023-08-28  Todd Valentic
#               Switch to async meter reading
#
##########################################################################

import asyncio
import functools
import importlib
import sys

from datatransport import ProcessClient, ConfigComponent, Directory, XMLRPCServer

from pymodbus.exceptions import ModbusException

from state_cache import StateCache


def valid_meter_name(func):
    """Decorator to ensure meter_name is valid"""

    @functools.wraps(func)
    def wrapper(self, meter_name, *pos, **kwargs):
        if meter_name not in self.meters:
            raise ValueError(f"Unknown meter name: {meter_name}")

        return func(self, meter_name, *pos, **kwargs)

    return wrapper

def valid_meter_name_or_all(func):
    """Decorator to ensure meter_name is valid"""

    @functools.wraps(func)
    def wrapper(self, meter_name, *pos, **kwargs):
        if meter_name != "all" and meter_name not in self.meters: 
            raise ValueError(f"Unknown meter name: {meter_name}")

        return func(self, meter_name, *pos, **kwargs)

    return wrapper



class Meter(ConfigComponent):
    """Meter component"""

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, "meter", *p, **kw)

        self.groups = self.config.get_list("groups")

        self.host = self.config.get("host", "localhost")
        port = self.config.get_int("port", 502)
        extra = self.config.get_list("extra")
        self.registermap = self.config.get_path("registermap", "map.json")

        kw = dict(entry.split("=") for entry in extra)

        module_name, class_name = self.config.get("type").rsplit(".", 1)

        module = importlib.import_module(module_name)
        factory = getattr(module, class_name)

        self.meter = factory(self.registermap, self.host, port=port, **kw)

        self.log.info("Connect to %s:%s", self.host, port)

    def __getattr__(self, name):
        """Proxy to underlying meter"""

        return getattr(self.meter, name)

    async def get_state(self):
        """Read the state"""

        try:
            registers = await self.meter.read_groups(self.groups)
        except (OSError, ModbusException) as err:
            self.log.error("Error reading: %s", err)
            return {}

        state = {}

        for register in registers.values():
            state[register.path] = {"value": register.value}

        values = await self.meter.read_virtual(state)

        if values:
            state.update(values)

        return {self.name: state}

    async def read_register_paths(self, paths):
        """Read regsiters from paths"""

        try:
            data = await self.meter.read_register_paths(paths)
        except (OSError, ModbusException) as err:
            self.log.error("Error reading: %s", err)
            return {}

        results = {}

        for reg in data:
            results[reg.path] = {"value": reg.value}

        return {self.name: results}


class MeterService(ProcessClient):
    """Meter XMLRPC Service Base"""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.directory = Directory(self)

        self.xmlserver = XMLRPCServer(self)
        self.main = self.xmlserver.main
        self.service_name = self.config.get("service.name")

        self.xmlserver.register_function(self.get_state)
        self.xmlserver.register_function(self.get_state_cache)
        self.xmlserver.register_function(self.update_state_cache)
        self.xmlserver.register_function(self.list_meters)
        self.xmlserver.register_function(self.list_groups)
        self.xmlserver.register_function(self.list_registers)
        self.xmlserver.register_function(self.list_register)
        self.xmlserver.register_function(self.list_register_details)
        self.xmlserver.register_function(self.read_group)
        self.xmlserver.register_function(self.control)
        self.xmlserver.register_function(self.list_controls)

        self.xmlserver.register_function(self.read_register_paths)
        self.xmlserver.register_function(self.read_register_path)
        self.xmlserver.register_function(self.read_register_addr)
        self.xmlserver.register_function(self.write_register_path)
        self.xmlserver.register_function(self.write_register_addr)

        self.cache = self.directory.connect("cache")
        self.meters = self.config.get_components("meters", factory=Meter)

        cache_timeout = self.config.get_timedelta("cache.timeout", "5m")
        self.cache.set_timeout(self.service_name, cache_timeout.total_seconds())
        self.log_cache_updates = self.config.get_boolean("cache.log", False)

        self.local_cache = StateCache()

    def log_cache(self, *args):
        """Log cache activity"""

        if self.log_cache_updates:
            self.log.info(*args)

    def list_meters(self):
        """List the meters"""

        return list(self.meters)

    def list_groups(self):
        """List the groups"""

        results = {}

        for name, meter in self.meters.items():
            results[name] = meter.list_groups()

        return results

    def list_registers(self):
        """List groups/registers for all meters"""

        results = {}

        for name, meter in self.meters.items():
            results[name] = meter.list_registers()

        return results

    def list_register_details(self):
        """List register mapping details for all meters"""

        results = {}

        for name, meter in self.meters.items():
            results[name] = meter.list_register_details()

        return results

    @valid_meter_name
    def list_register(self, meter_name, path):
        """List register values at path"""

        return self.meters[meter_name].list_register(path)

    @valid_meter_name
    def read_register_path(self, meter_name, path):
        """Read register at meter path"""

        return asyncio.run(self.meters[meter_name].read_register_path(path))

    @valid_meter_name
    def read_register_addr(self, meter_name, addr, num_words=1):
        """Read register at meter addr"""

        addr = int(addr)
        num_words = int(num_words)

        return asyncio.run(self.meters[meter_name].read_registers_addr(addr, num_words))

    @valid_meter_name
    def write_register_path(self, meter_name, path, *values):
        """Write a value to a meter"""

        values = [int(x) for x in values]

        return asyncio.run(self.meters[meter_name].write_register_path(path, *values))

    @valid_meter_name
    def write_register_addr(self, meter_name, addr, *values):
        """Write values to a meter"""

        addr = int(addr)
        values = [int(x) for x in values]

        return asyncio.run(self.meters[meter_name].write_register_addr(addr, *values))

    @valid_meter_name
    def read_group(self, meter_name, group_name):
        """Read registers in meter group"""

        return asyncio.run(self.meters[meter_name].read_group(group_name))

    @valid_meter_name_or_all
    def control(self, meter_name, cmd):
        """Execute control command"""

        if meter_name == "all":
            meters = [meter for meter in self.meters.values()] 
        else:
            meters = [self.meters[meter_name]] 

        results = asyncio.run(self.run_meter_command(meters, "control", cmd))

        if meter_name == "all":
            return results 

        return results[0]


    def list_controls(self):
        """List control commands"""

        return {m.name: m.list_controls() for m in self.meters.values()}

    def make_path_lists(self, *paths):
        """Flatten paths into a list"""

        if len(paths) == 1 and isinstance(paths[0], dict):
            return paths[0]

        if not paths:
            raise ValueError("No meter specified")

        meter_name, paths = paths[0], paths[1:]

        if meter_name not in self.meters:
            raise ValueError(f"Unknown meter name: {meter_name}")

        pathlist = []

        for path in paths:
            if isinstance(path, (list, set, tuple)):
                pathlist.extend(path)
            else:
                pathlist.append(path)

        return {meter_name: pathlist}

    def read_register_paths(self, *paths):
        """Update state with registers in path"""

        pathlists = self.make_path_lists(*paths)

        # Get current cached data or read new if missing.

        state = self.local_cache.get() or self.get_state_cache()

        if not state:
            return None

        online_meters = [m.name for m in self.get_online_meters()]

        meterpaths = {}

        for meter_name, pathlist in pathlists.items():
            if meter_name not in online_meters:
                continue
            meter = self.meters[meter_name]
            meterpaths[meter] = pathlist

        results = asyncio.run(self.read_meter_paths(meterpaths))

        output = {}

        for entry in results:
            for meter_name, values in entry.items():
                state["meters"][meter_name].update(values)
                output[meter_name] = values

        self.local_cache.update(state)
        self.cache.put("genset", state)

        self.log_cache("Update state cache %s", list(output))

        return output

    def update_state_cache(self, *paths):
        """Update state with registers in path. Return full state"""

        pathlists = self.make_path_lists(*paths)

        if not self.local_cache.is_valid():
            state = self.get_state()
            if not state:
                return None
            for meter_name, pathlist in pathlists.items():
                registers = set(state["meters"][meter_name])
                missingpaths = list(set(pathlist).difference(registers))
                pathlists[meter_name] = missingpaths

        if self.read_register_paths(pathlists):
            return self.local_cache.get()

        return None

    def get_state_cache(self, max_age=15):
        """Get state from cache or update"""

        if self.local_cache.is_valid(float(max_age)):
            self.log_cache("Use genset cache")
            return self.local_cache.get()

        return self.get_state()

    def get_online_meters(self):
        """Return list of meters that are online"""

        hosts_online = self.cache.get_or_default("network", None)

        if not hosts_online:
            return None

        return [m for m in self.meters.values() if m.host in hosts_online]

    def get_state(self):
        """Get overall state, error handler"""

        try:
            return self._get_state()
        except:
            self.log.exception("Problem in get_state()")
            raise

    def _get_state(self):
        """Get overall state"""

        regmap = {m.name: m.registermap.name for m in self.meters.values()}

        state = {}
        state["meters"] = {}
        state["meta"] = {
            "timestamp": self.now(),
            "version": 3,
            "regmap": regmap, 
        }

        online_meters = self.get_online_meters()

        self.log_cache("Read new state")

        readings = asyncio.run(self.read_meter_states(online_meters))

        for values in readings:
            state["meters"].update(values)

        if not state["meters"]:
            self.cache.clear(self.service_name)
            self.local_cache.clear()
            return None

        self.cache.put(self.service_name, state)
        self.local_cache.put(state)

        return state

    async def read_meter_states(self, meters):
        """Read state from each meter"""

        if not meters:
            return []

        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(meter.get_state()) for meter in meters]

        return [task.result() for task in tasks]

    async def read_meter_paths(self, meterpaths):
        """Read registers from each meter"""

        async with asyncio.TaskGroup() as group:
            tasks = []
            for meter, paths in meterpaths.items():
                task = group.create_task(meter.read_register_paths(paths))
                tasks.append(task)

        return [task.result() for task in tasks]

    async def run_meter_command(self, meters, cmd, *options):
        """Run a command on all meters"""

        async with asyncio.TaskGroup() as group:
            tasks = []
            for meter in meters: 
                func = getattr(meter, cmd)
                task = group.create_task(func(*options))
                tasks.append(task)

        return [task.result() for task in tasks]


    
if __name__ == "__main__":
    MeterService(sys.argv).run()
