#!/usr/bin/env python3
"""Collect system status"""

##########################################################################
#
#   Collect and post a snapshot of the computer health:
#
#       - disk usage
#       - memory usage
#       - processor load
#       - uptime
#       - network usage
#
#   2007-09-12  Todd Valentic
#       Initial implementation. Based on the
#           ResourceMonitor component
#
#   2009-09-22  Todd Vaelntic
#       Relax constraint on /proc/mounts to include
#           file systems with no device (to pick up /tmp).
#
#   2021-05-24  Todd Valentic
#       Add MAC address for Ethernet devices
#
#   2021-08-15  Todd Valentic
#       Add temperature section
#
#   2023-07-07  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import configparser
import io
import glob
import os
import pathlib

from datetime import datetime

class ResourceMonitor:
    """Resource monitor"""

    def __init__(self):
        self.lasttx = {}
        self.lastrx = {}

    def read(self, path):
        """Read data file"""

        return pathlib.Path(path).read_text('utf-8')

    def readlines(self, path):
        """Read data file, return lines"""

        return self.read(path).split('\n')


    def update_mounts(self, stats):
        """Update disk mounts"""

        mounts = self.readlines("/proc/mounts")
        mounts = [x for x in mounts if len(x)]
        mounts = [x.split()[0:4] for x in mounts]

        paths = []

        for device, path, fstype, access in mounts:
            try:
                info = os.statvfs(path)
            except: # pylint: disable=bare-except
                continue

            if info.f_blocks == 0:
                continue

            if stats.has_section(path):
                continue

            paths.append(path)

            totalbytes = info.f_blocks * info.f_bsize
            freebytes = info.f_bavail * info.f_bsize
            reserved = info.f_bfree * info.f_bsize - freebytes
            totalavail = totalbytes - reserved
            usedbytes = totalavail - freebytes
            usedpct = usedbytes / float(totalavail) * 100

            stats.add_section(path)
            stats.set(path, "device", device)
            stats.set(path, "fstype", fstype)
            stats.set(path, "access", access)
            stats.set(path, "totalbytes", str(totalavail))
            stats.set(path, "freebytes", str(freebytes))
            stats.set(path, "usedbytes", str(usedbytes))
            stats.set(path, "usedpct", str(usedpct))

        stats.set("System", "mounts", " ".join(paths))

    def update_memory(self, stats):
        """Update memory usage"""

        lines = self.readlines("/proc/meminfo")

        if "total:" in lines[0]:  # old style format
            lines = lines[3:]

        section = "Memory"
        stats.add_section(section)

        for line in lines:
            try:
                key, value = line.split(":")
                value = int(value.split()[0]) * 1024
                stats.set(section, key, str(value))
            except: # pylint: disable=bare-except
                pass

    def update_load(self, stats):
        """Update system load"""

        info = self.readlines("/proc/loadavg")
        load = info[0].split()

        section = "Load"

        stats.add_section(section)
        stats.set(section, "1min", load[0])
        stats.set(section, "5min", load[1])
        stats.set(section, "15min", load[2])

    def update_swaps(self, stats):
        """Update swap usage"""

        section = "Swaps"
        stats.add_section(section)

        info = self.readlines("/proc/swaps")

        swaps = []

        for line in info[1:-1]:
            try:
                dev, swaptype, size, used, priority = line.split()
            except: # pylint: disable=bare-except
                continue
            swaps.append(dev)
            stats.set(section, dev + ".type", swaptype)
            stats.set(section, dev + ".size", str(int(size) * 1024))
            stats.set(section, dev + ".used", str(int(used) * 1024))
            stats.set(section, dev + ".priority", priority)

        stats.set(section, "mounts", " ".join(swaps))

    def update_uptime(self, stats):
        """Compute uptime"""

        info = self.readlines("/proc/uptime")
        secs = float(info[0].split()[0])

        section = "Uptime"
        stats.add_section(section)
        stats.set(section, "seconds", str(secs))

    def compute_rate(self, prevbytes, prevtime, curbytes, curtime):
        """Compute tx/rx rates"""

        if prevbytes > curbytes:
            # Counter rollover
            deltabytes = 2**32 - prevbytes + curbytes
        else:
            deltabytes = curbytes - prevbytes
        return deltabytes / (curtime - prevtime).seconds

    def get_macaddr(self, interface):
        """Return the MAC addres of the network interface"""

        return self.read(f"/sys/class/net/{interface}/address").strip()

    def update_network(self, stats):
        """Update network statistics"""

        info = self.readlines('/proc/net/dev')[2:-1]

        section = "Network"
        stats.add_section(section)

        devs = []
        now = datetime.now()

        for device in info:
            name, data = device.split(":")
            name = name.strip()
            data = data.split()

            if name in self.lasttx:
                txbytes, txtime = self.lasttx[name]
                rxbytes, rxtime = self.lastrx[name]
                txrate = self.compute_rate(txbytes, txtime, float(data[8]), now)
                rxrate = self.compute_rate(rxbytes, rxtime, float(data[0]), now)
            else:
                txrate = 0
                rxrate = 0

            stats.set(section, name + ".macaddr", self.get_macaddr(name))
            stats.set(section, name + ".rx.rate", str(rxrate))
            stats.set(section, name + ".rx.bytes", data[0])
            stats.set(section, name + ".rx.packets", data[1])
            stats.set(section, name + ".rx.errs", data[2])
            stats.set(section, name + ".rx.drop", data[3])

            stats.set(section, name + ".tx.rate", str(txrate))
            stats.set(section, name + ".tx.bytes", data[8])
            stats.set(section, name + ".tx.packets", data[9])
            stats.set(section, name + ".tx.errs", data[10])
            stats.set(section, name + ".tx.drop", data[11])

            self.lasttx[name] = (float(data[8]), now)
            self.lastrx[name] = (float(data[0]), now)

            devs.append(name)

        stats.set(section, "devices", " ".join(devs))

    def update_temps(self, stats):
        """Update temperature sensors"""

        zones = glob.glob("/sys/class/thermal/thermal_zone*")

        section = "Temperature"
        stats.add_section(section)

        for zone in sorted(zones):
            path = pathlib.Path(zone, "temp")
            temp_c = path.read_text('utf-8').strip()
            temp_c = float(temp_c) / 1000
            stats.set(section, os.path.basename(zone), str(temp_c))

    def status(self):
        """Gather status"""

        timestamp = datetime.now()

        stats = configparser.ConfigParser()
        stats.add_section("System")
        stats.set("System", "timestamp", str(timestamp))

        self.update_mounts(stats)
        self.update_memory(stats)
        self.update_load(stats)
        self.update_uptime(stats)
        self.update_network(stats)
        self.update_swaps(stats)
        self.update_temps(stats)

        buffer = io.StringIO()
        stats.write(buffer)

        return buffer.getvalue()


if __name__ == "__main__":
    monitor = ResourceMonitor()
    print(monitor.status())
