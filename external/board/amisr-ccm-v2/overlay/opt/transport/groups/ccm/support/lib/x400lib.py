#!/usr/bin/env python3

##########################################################################
#
#   ControlByWire X400 series interface library
#
#   2023-06-04  Todd Valentic
#               Initial implementation
#
##########################################################################

import requests

class X400():

    def __init__(self, host, port=80, scheme='http', auth=None):
        self.auth = auth
        self.url = f"{scheme}://{host}:{port}/state.json" 

    def get_state(self):
        response = requests.get(self.url, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def set(self, key, value):
        params = dict([(key, str(value))])
        response = requests.get(self.url, auth=self.auth, params=params)
        response.raise_for_status()

if __name__ == '__main__':

    import pprint

    x400 = X400(host='localhost',port=9000)

    print('State:')
    pprint.pprint(x400.get_state())

    print("Set relay1 to '0'")
    x400.set('relay1','0')
    pprint.pprint(x400.get_state())

    print("Set relay1 to 1")
    x400.set('relay1',1)
    pprint.pprint(x400.get_state())

