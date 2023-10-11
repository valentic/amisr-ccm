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

from datatransport import (
    ProcessClient,
    ConfigComponent,
    Directory,
    XMLRPCServer
)

from pymodbus.exceptions import ModbusException

def valid_meter_name(func):
    """Decorator to ensure meter_name is valid"""

    @functools.wraps(func)
    def wrapper(self, meter_name, *pos, **kwargs):

        if meter_name not in self.meters:
            raise ValueError(f"Unknown meter name: {meter_name}")

        return func(self, meter_name, *pos, **kwargs)

    return wrapper

class Meter(ConfigComponent):
    """Meter component"""

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, 'meter', *p, **kw)

        self.groups = self.config.get_list('groups')

        self.host = self.config.get('host', 'localhost')
        port = self.config.get_int('port', 502)
        extra = self.config.get_list('extra') 
        self.registermap = self.config.get_path('registermap', 'map.json')

        kw = dict(entry.split('=') for entry in extra)

        module_name, class_name = self.config.get('type').rsplit(".", 1) 

        module = importlib.import_module(module_name)
        factory = getattr(module, class_name)

        self.meter = factory(self.registermap, self.host, port=port, **kw) 

        self.log.info('Connect to %s:%s', self.host, port)

    def __getattr__(self, name):
        """Proxy to underlying meter"""

        return getattr(self.meter, name)

    async def get_state(self):

        try:
            data = await self.meter.read_groups(self.groups)
        except (OSError, ModbusException) as err:
            self.log.error("Error reading: %s", err)
            return {} 

        state = {}

        for group, registers in data.items():
            values = {}
            for reg in registers:
                values[reg.path] = {
                    'value': reg.value,
                    'unit': reg.unit,
                    'description': reg.description,
                    'address': reg.address
                }
            state[group] = values

        values = await self.meter.read_virtual(state)

        if values:
            state["Virtual"] = values

        return {self.name: state}

class MeterService(ProcessClient):

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.directory = Directory(self)

        self.xmlserver = XMLRPCServer(self)
        self.main = self.xmlserver.main
        self.service_name = self.config.get('service.name')

        self.xmlserver.register_function(self.get_state)
        self.xmlserver.register_function(self.list_meters)
        self.xmlserver.register_function(self.list_groups)
        self.xmlserver.register_function(self.list_registers)
        self.xmlserver.register_function(self.list_register)
        self.xmlserver.register_function(self.list_register_details)
        self.xmlserver.register_function(self.read_group)
        self.xmlserver.register_function(self.control)
        self.xmlserver.register_function(self.list_controls)

        self.xmlserver.register_function(self.read_register_path)
        self.xmlserver.register_function(self.read_register_addr)
        self.xmlserver.register_function(self.write_register_path)
        self.xmlserver.register_function(self.write_register_addr)

        self.cache = self.directory.connect('cache')
        self.meters = self.config.get_components('meters', factory=Meter)

        cache_timeout = self.config.get_timedelta('cache.timeout', '5m')
        self.cache.set_timeout(self.service_name, cache_timeout.total_seconds()) 

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

    @valid_meter_name
    def control(self, meter_name, cmd):
        """Execute control command"""

        return asyncio.run(self.meters[meter_name].control(cmd))

    def list_controls(self):
        """List control commands"""

        return { m.name: m.list_controls() for m in self.meters.values() }

    def get_state(self):
        """Get overall state, error handler"""

        try:
            return self._get_state()
        except:
            self.log.exception("Problem in get_state()")
            raise

    def _get_state(self):
        """Get overall state"""

        hosts_online = self.cache.get_or_default('network', None)

        if not hosts_online:
            return None

        regmap = {}

        results = {}
        results['meters'] = {}
        results['meta'] = { 
            "timestamp": self.now(), 
            "version": 2, 
            "regmap": {m.name: m.registermap.name for m in self.meters.values()} 
        }

        online_meters = [m for m in self.meters.values() if m.host in hosts_online]

        readings = asyncio.run(self.read_meters(online_meters))

        for values in readings:
            results['meters'].update(values)

        if not results['meters']:
            return None

        self.cache.put(self.service_name, results)

        return results

    async def read_meters(self, meters):

        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(meter.get_state()) for meter in meters]

        return [task.result() for task in tasks]

if __name__ == '__main__':
    MeterService(sys.argv).run()
