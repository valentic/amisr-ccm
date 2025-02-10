#!/usr/bin/env python3
"""PDU Control Service"""

##########################################################################
#
#   X400 control service
#
#   This service is used to access the ControlByWeb X400 device. 
#
#   2023-07-21  Todd Valentic
#               Initial implementation 
#
#   2025-02-10  Todd Valentic
#               Add timeout for HTTP get request calls (default 5s)
#               Add timeout parameter to config file 
#
##########################################################################

import sys

import requests

from datatransport import ProcessClient
from datatransport import XMLRPCServer
from datatransport import Directory

# pylint: disable=bare-except

class Server(ProcessClient):
    """X400 Control Server"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.xmlserver = XMLRPCServer(self)
        self.main = self.xmlserver.main
        self.directory = Directory(self)
        self.service_name = self.config.get('service.name')

        scheme = self.config.get('device.scheme', 'http')
        host = self.config.get('device.host', 'localhost')
        port = self.config.get_int('device.port', 80)
        self.timeout = self.config.get_timedelta('device.timeout', 5)

        self.url = f"{scheme}://{host}:{port}" 
        self.auth = self.config.get('device.auth')

        if self.auth:
            self.auth = self.auth.split(':')

        self.xmlserver.register_function(self.get_state)
        self.xmlserver.register_function(self.set_output)

        self.cache = self.directory.connect("cache")

        self.log.info(f"Communicating with {self.url}")

    def call(self, path, params=None):    
        url = f"{self.url}/{path}"
        response = requests.get(
            url, 
            auth=self.auth, params=params, 
            timeout=self.timeout.total_seconds()
        )
        response.raise_for_status()
        return response

    def get_state(self):
        """Return state from X400"""

        results = {}

        results['state'] = self.call('state.json').json()
        results['customState'] = self.call('customState.json').json()

        self.cache.put(self.service_name, results)

        return results

    def set_output(self, name, state):
        """Set output state"""

        self.log.info('%s -> %s', name, state)

        params = dict([(name, str(state))])
        self.call('state.json', params=params)

        return self.get_state() 

if __name__ == "__main__":
    Server(sys.argv).run()
