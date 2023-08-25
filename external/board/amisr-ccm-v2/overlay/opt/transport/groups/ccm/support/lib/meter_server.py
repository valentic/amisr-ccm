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
##########################################################################

import importlib
import sys

from datatransport import (
    ProcessClient,
    ConfigComponent,
    Directory,
    XMLRPCServer
)

from pymodbus.exceptions import ModbusException

class Meter(ConfigComponent):

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

    def read(self):
        results = {}

        for group in self.groups:
            results[group] = self.meter.read(group)

        return results

class MeterService(ProcessClient):

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.directory = Directory(self)

        self.xmlserver = XMLRPCServer(self)
        self.main = self.xmlserver.main
        self.service_name = self.config.get('service.name')

        self.xmlserver.register_function(self.get_state)

        self.cache = self.directory.connect('cache')
        self.meters = self.config.get_components('meters', factory=Meter)

        cache_timeout = self.config.get_timedelta('cache.timeout', '5m')
        self.cache.set_timeout(self.service_name, cache_timeout.total_seconds()) 

    def get_state(self):
        try:
            return self._get_state()
        except:
            self.log.exception("Problem in get_state()")
            raise

    def _get_state(self):

        hosts_online = self.cache.get_or_default('network', None)

        if not hosts_online:
            return None

        regmap = {}

        results = {}
        results['meters'] = {}
        results['meta'] = { "timestamp": self.now(), "version": 2, "regmap": regmap }

        for meter in self.meters.values():

            if meter.host not in hosts_online:
                continue

            try:
                data = meter.read()
            except OSError as err: 
                self.log.error("%s: %s", meter.name, err)
                continue 
            except ModbusException as err:
                self.log.error("%s: %s", meter.name, err)
                continue 

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

            results['meters'][meter.name] = state 
            regmap[meter.name] = meter.registermap.name

        if not results['meters']:
            return None

        self.cache.put(self.service_name, results)

        return results

if __name__ == '__main__':
    MeterService(sys.argv).run()