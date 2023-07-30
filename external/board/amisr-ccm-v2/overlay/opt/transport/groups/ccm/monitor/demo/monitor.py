#!/usr/bin/env python3

##########################################################################
#
#   Demo Data Monitor
#
#   Used to help port/test code 
#
#   2023-06-16  Todd Valentic
#               Initial implementation
#
##########################################################################

import struct
import sys

from datamonitor import DataMonitor

class DemoMonitor(DataMonitor):

    def __init__(self, argv):
        DataMonitor.__init__(self, argv)

        cache_timeout = self.config.get_timedelta('cache.timeout')

        if cache_timeout:
            secs = cache_timeout.total_seconds()
            self.cache_service.set_timeout('demo', secs)
            self.log.info('Setting cache timeout to %s' % cache_timeout)

        self.count = 0 

        self.log.info('Ready to start')

    def update(self, data):
        self.put_cache('demo', data)

    def sample(self):

        self.count += 1
        self.update(self.count)
        self.log.info(f"Count {self.count}")

        return dict(count=self.count) 

    def write(self, output, timestamp, data):

        version = 1

        output.write(struct.pack('!B',version))
        output.write(struct.pack('!i',int(timestamp)))
        output.write(struct.pack('!i',data['count']))

if __name__ == '__main__':
    DemoMonitor(sys.argv).run()
