#!/usr/bin/env python3
"""Ping Toolkit"""

###########################################################################
#
#   Ping toolkit
#
#   2023-08-24  Todd Valentic
#               Initial implementation
#
###########################################################################

import subprocess

class Pinger:

    def __init__(self, host, count=10, timeout=10):

        self.host = host
        self.count = count
        self.timeout = timeout

        self.cmd = f"ping -4 -c {count} -W {timeout} -q {host}"

    def collect(self):
        """Collect a data snapshot, return as json or None if failure"""

        status, output = subprocess.getstatusoutput(self.cmd)

        if status != 0:
            return None

        return self.parse(output)

    def parse(self, output):

        # Example output:
        # PING toddvalentic.com (45.33.53.117) 56(84) bytes of data.
        #
        # --- toddvalentic.com ping statistics ---
        # 10 packets transmitted, 10 received, 0% packet loss, time 9020ms
        # rtt min/avg/max/mdev = 29.844/45.944/70.515/12.746 ms
        #
        # sometimes there is an error field between received and packet loss

        output = output.split("\n")

        host_stats = output[0].split()
        xmit_stats = output[-2].split(",")
        timing_stats = output[-1].split("=")[1].split()[0].split("/")

        results = {
            'destination': host_stats[1],
            'destination_ip': host_stats[2][1:-1],
            'packets_transmitted': int(xmit_stats[0].split()[0]),
            'packets_received': int(xmit_stats[1].split()[0]),
            'packet_loss_percent': float(xmit_stats[-2].split("%")[0]),
            'time_ms': float(xmit_stats[-1].split()[1].replace('ms','')),
            'round_trip_ms_min': float(timing_stats[0]),
            'round_trip_ms_avg': float(timing_stats[1]),
            'round_trip_ms_max': float(timing_stats[2]),
            'round_trip_ms_stddev': float(timing_stats[3]),
        }

        return results 

def test():
    import sys
    import json

    ping = Pinger(sys.argv[1], count=2)

    results = ping.collect()

    print(json.dumps(results))

if __name__ == '__main__':
    test()

