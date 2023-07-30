#!/usr/bin/env python3
"""Inbound SBD message Handler"""

##########################################################################
#
#   Handle inbound SBD messages
#
#   The first byte of the payload indicates the message type:
#
#       0 - CCM command
#       1 - Shell command
#       2 - File upload
#
#   2023-07-11  Todd Valentic
#               Initial implementation. Based on HBR SBD.
#
####################################################################@@@@@@

import sys

from pathlib import Path

from datatransport import ProcessClient, NewsPoller
from datatransport import newstool

from sbd_types import MessageType
from sbd_filehandler import SBDFileHandler


class SBDInboundMonitor(ProcessClient):
    """Inbound SBD message monitor"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poller = NewsPoller(self, callback=self.process)
        self.main = self.news_poller.main

        self.path_file_ack = self.config.get_path("path.file_ack")

    def process_shell_command(self, _payload):
        """Process SHELL_COMMAND messages"""

        self.log.info(" - shell command")
        self.log.info("Not implemented yet")

    def process_ccm_command(self, _payload):
        """Process CCM_COMMAND messages"""

        self.log.info(" - ccm command")
        self.log.info("Not implemented yet")

    def process_file_upload(self, payload):
        """Process FILE_UPLOAD messages"""

        self.log.info(" - File upload")

        ack = SBDFileHandler(self.log).process(payload)

        if ack:
            filename = Path(self.now().strftime(self.path_file_ack))

            filename.parent.mkdir(parents=True, exist_ok=True)
            filename.write_bytes(ack)

            self.log.info("  - sent ack %s", filename)

    def process_message(self, data):
        """Dispatch SBD message corresponding handler"""

        msgtype = ord(data[0])
        payload = data[1:]

        handlers = {
            MessageType.CCM_COMMAND: self.process_ccm_command,
            MessageType.SHELL_COMMAND: self.process_shell_command,
            MessageType.FILE_UPLOAD: self.process_file_upload,
        }

        if msgtype in handlers:
            handlers[msgtype](payload)
        else:
            self.log.error(" - Unknown message type: %s", msgtype)

    def process(self, message):
        """Process inboud SBD message"""

        self.log.info("Message received")

        for filename in newstool.save_files(message):
            path = Path(filename)
            data = path.read_bytes().strip()

            try:
                self.process_message(data)
            except:  # pylint: disable=bare-except
                self.log.exception("Problem processing payload")

            path.unlink()


if __name__ == "__main__":
    SBDInboundMonitor(sys.argv).run()
