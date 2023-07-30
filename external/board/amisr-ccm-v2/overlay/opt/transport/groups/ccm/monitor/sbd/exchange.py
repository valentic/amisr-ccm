#!/usr/bin/env python3
"""SBD Data Exchange"""

# pylint: disable=bare-except

##########################################################################
#
#   SBD Data Exchange
#
#   Send files in the listed output directories via SBD and check for
#   any incoming messages. Each data source is classified by a code
#   and prioritized to ensure that the most important messages get 
#   out first. The limit_files option can be used to select only the 
#   newest files.
#
#   2017-10-16  Todd Valentic
#               Initial implementation
#
#   2018-06-17  Todd Valentic
#               Move file limits into the source component
#
#   2019-05-095 Todd Valentic
#               Add modem check
#
#   2023-06-16  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import glob
import os
import sys

from datamonitor import DataMonitor
from datatransport import ConfigComponent, NewsPoster

import modem


class Source(ConfigComponent):
    """Data Source"""

    def __init__(self, *pos, **kw):
        ConfigComponent.__init__(self, "source", *pos, **kw)

        self.code = self.config.get_int("code")
        self.file_pattern = self.config.get("files")
        self.limit_files = self.config.get_int("limit_files")
        self.priority = self.config.get_int("priority")

    def extract_date(self, filename):
        """Parse data from filename"""

        # Format: <source>-YYYYMMDD-HHMMSS.<ext>[.<ext>]
        basename = os.path.basename(filename)
        date = basename.split("-", 1)[1].split(".", 1)[0]
        return date

    def find_filenames(self):
        """Search for new filenames"""

        filenames = glob.glob(os.path.join(self.file_pattern))
        filenames = sorted(filenames, key=self.extract_date)

        if self.limit_files and len(filenames) > self.limit_files:
            self.log.info("Limiting files to last %d", self.limit_files)
            removal_list = filenames[0 : -self.limit_files]
            filenames = filenames[-self.limit_files :]

            for filename in removal_list:
                os.remove(filename)

        return filenames


class SBDMonitor(DataMonitor):
    """SBD Data Monitor"""

    def __init__(self, argv):
        DataMonitor.__init__(self, argv)

        self.news_poller = NewsPoster(self)

        devices = self.config.get_list("iridium.devices")
        modem_dev = None

        self.log.info("Scanning for modems:")

        for device in devices:
            self.log.info("  - %s", device)

            if os.path.exists(f"/dev/{device}"):
                modem_dev = device
                break

        if not modem_dev:
            self.abort("No modem found")

        self.log.info("Iridium device found: %s", modem_dev)

        self.modem = modem.Modem(modem_dev, log=self.log, is_alive=self.is_running)

        sources = self.config.get_components("sources", factory=Source)
        sources = dict(sorted(sources.items(), key=lambda x: x[1].priority))

        self.sources = sources

    def find_filenames(self):
        """Find data files"""

        filenames = []

        for source in self.sources.values():
            filenames.extend(source.find_filenames())

        return filenames

    def buffer_data(self, filename):
        """Write filename payload to modem"""

        basename = os.path.basename(filename)
        srcname = basename.split("-", 1)[0]
        source = self.sources[srcname]

        with open(filename, "rb") as f:
            data = chr(source.code) + f.read()

        self.log.info("MO message queued (%d bytes)", len(data))
        self.modem.writeMessage(data)

    def exchange_data(self):
        """Send message, check for inbound"""

        inbound_messages = self.modem.exchangeSBD()

        for msg in inbound_messages:
            with open("msg.sbd", "wb") as f:
                f.write(msg)
            self.newsPoster.post("msg.sbd")

    def wait_for_signal(self):
        """Wait until sufficient signal strength"""

        try:
            self.modem.wait_for_signal()
            return True
        except:  # pylint: disable=bare-except
            return False

    def modem_check(self):
        """Check if modem is ready"""

        self.log.info("Modem check")

        try:
            self.modem.ready()
        except modem.Timeout:
            self.log.error("  - timeout")
            return False
        except:
            self.log.exception("Problem communicating with modem")
            return False

        return True

    def sample(self):
        """Process queued data messages"""

        if not self.modem_check():
            return None

        filenames = self.find_filenames()

        if filenames:
            self.log.info("Found %d files queued for transfer", len(filenames))

            for index, filename in enumerate(filenames):
                self.log.info(
                    "Send %d of %d: %s",
                    index + 1,
                    len(filenames),
                    os.path.basename(filename),
                )
                self.buffer_data(filename)
                self.exchange_data()
                os.remove(filename)
                self.log.info("  All messages sent")

        else:
            if self.wait_for_signal() and self.modem.status_sbd()["raFlag"]:
                self.log.info("  Ring alert detected")
                self.exchange_data()

        return None


if __name__ == "__main__":
    SBDMonitor(sys.argv).run()
