#!/usr/bin/env python3
"""XMLRPC directory service access"""

##########################################################################
#
#   Access to the directory service outside of data transport.
#
#   2005-11-11  Todd Valentic
#               Initial implementation.
#
#   2007-03-23  Todd Valentic
#               Added default timeout.
#
#   2021-07-13  Todd Valentic
#               Add module connect() method
#
#   2023-06-05  Todd Valentic
#               Updates for Python3
#
##########################################################################

import socket
import xmlrpc.client

socket.setdefaulttimeout(15)


class Directory:
    """Directory class"""

    def __init__(self, host="localhost", port=8411):
        url = f"http://{host}:{port}"
        self.directory = xmlrpc.client.ServerProxy(url)

    def connect(self, service_name):
        """Return a client proxy connection to an XMLRPC service"""

        url = self.directory.get(service_name, "url")
        return xmlrpc.client.ServerProxy(url)


def connect(service_name, *pos, **kw):
    """Forward connect() call to directory"""

    return Directory(*pos, **kw).connect(service_name)


if __name__ == "__main__":
    # Example usage - connect to beamcode service:

    directory = connect("directory")

    print(directory.list())
