#!/usr/bin/env python3
"""Victron Interface Service"""

##########################################################################
#
#   XMLRPC service for accessing the genset comap controllers
#
#   2023-08-03  Todd Valentic
#               Initial implementation 
#
##########################################################################

import sys

from datatransport import (
    ProcessClient,
    ConfigComponent,
    Directory,
    XMLRPCServer
)

from pymodbus.exceptions import ModbusException

from genset import Genset 

class GensetMeter(ConfigComponent):

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, 'genset', *p, **kw)

        self.groups = self.config.get_list('groups')

        host = self.config.get('host', 'localhost')
        port = self.config.get_int('port', 502)
        regmap = self.config.get('registermap', 'map.txt')
        access_code = self.config.get_int('access_code', 0)

        self.meter = Genset(regmap, host, port=port, access_code=access_code)

        self.log.info('Connect to %s:%s', host, port)

    def read(self):
        results = {}

        for group in self.groups:
            results[group] = self.meter.read(group)

        return results

class GensetService(ProcessClient):

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.directory = Directory(self)

        self.xmlserver = XMLRPCServer(self)
        self.main = self.xmlserver.main
        self.service_name = self.config.get('service.name')

        self.xmlserver.register_function(self.get_state)

        self.cache = self.directory.connect('cache')
        self.meters = self.config.get_components('gensets', factory=GensetMeter)

        cache_timeout = self.config.get_timedelta('cache.timeout', '5m')
        self.cache.set_timeout(self.service_name, cache_timeout.total_seconds()) 

    def get_state(self):
        try:
            return self._get_state()
        except:
            self.log.exception("Problem in get_state()")
            raise

    def _get_state(self):

        results = {'meters': {}}

        timestamp = self.now()

        for meter in self.meters.values():
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

        if not results['meters']:
            return None

        results['meta'] = { 'timestamp': timestamp }
        self.cache.put(self.service_name, results)

        return results

if __name__ == '__main__':
    GensetService(sys.argv).run()
