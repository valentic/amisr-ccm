#!/usr/bin/env python3
"""PDU Control Service"""

##########################################################################
#
#   Digial Loggers web power switch control service
#
#   This service is used to access the web power switch device rest API
#
#   https://www.digital-loggers.com/rest.html
#
#   2023-10-06  Todd Valentic
#               Initial implementation 
#
##########################################################################

import sys

import requests
from requests.auth import HTTPDigestAuth

from datatransport import ProcessClient
from datatransport import XMLRPCServer
from datatransport import Directory
from datatransport import ConfigComponent

# pylint: disable=bare-except

class WebPower(ConfigComponent):
    """WebPower Control Device"""

    def __init__(self, *args):
        ConfigComponent.__init__(self, "switch", *args)

        scheme = self.config.get('scheme', 'http')
        host = self.config.get('host', 'localhost')
        port = self.config.get_int('port', 80)

        self.url = f"{scheme}://{host}:{port}" 
        self.auth = self.config.get('auth')

        if self.auth:
            self.auth = HTTPDigestAuth(*self.auth.split(':'))

        self.log.info(f"Communicating with {self.url}")

    def call_get(self, path, params=None):    
        url = f"{self.url}/{path}"
        response = requests.get(url, auth=self.auth, params=params)
        response.raise_for_status()
        return response

    def call_put(self, path, data=None):
        url = f"{self.url}/{path}"
        headers = {"X-CSRF": "x"} 

        response = requests.put(url, auth=self.auth, data=data, headers=headers) 
        response.raise_for_status()

        return response

    def get_state(self):
        """Return relay state"""

        data = self.call_get("restapi/relay/outlets/").json()

        result = { str(relay+1): v for relay, v in enumerate(data) } 
    
        return result

    def set_outlet(self, outlet, state):
        """Set output state"""

        self.log.info('%s -> %s', outlet, state)

        data = {}

        if state == "on":
            data["value"] = "true"
        elif state == "off":
            data["value"] = "false"
        else:
            raise ValueError(f"Unknown state: {state}")

        relay = outlet - 1

        self.call_put(f"restapi/relay/outlets/{relay}/state/", data=data) 

        return self.get_state() 

class Server(ProcessClient):
    """WebPower Control Server"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.xmlserver = XMLRPCServer(self)
        self.main = self.xmlserver.main
        self.directory = Directory(self)
        self.service_name = self.config.get('service.name')

        self.switches = self.config.get_components("switches", factory=WebPower)

        self.xmlserver.register_function(self.get_state)
        self.xmlserver.register_function(self.get_state_pdu)
        self.xmlserver.register_function(self.set_outlet)

        self.cache = self.directory.connect("cache")

    def get_state_pdu(self, switch_name):
        """Return relay state for a pdu"""

        results = {}

        try:
            return self.switches[switch_name].get_state()
        except Exception as err:
            self.log.error("Problem reading: %s", err)

        return None 


    def get_state(self):
        """Return relay state"""

        results = {}

        for switch in self.switches.values():
            data = switch.get_state()
            if data:
                results[switch.name] = data

        self.cache.put(self.service_name, results)

        return results

    def set_outlet(self, name, outlet, state):
        """Set output state"""

        outlet = int(outlet)

        return self.switches[name].set_outlet(outlet, state)

if __name__ == "__main__":
    Server(sys.argv).run()
