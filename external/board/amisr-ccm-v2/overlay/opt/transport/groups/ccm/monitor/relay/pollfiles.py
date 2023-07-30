#!/usr/bin/env python3
"""Poll newsgroups for new files"""

############################################################################
#
#   Poll newsgroups for new files
#
#   A modern take (although much less capable) version of ArchiveGroups
#
#   2021-07-15  Todd Valentic
#               Initial implementation. Based on postfiles.py
#
#   2023-07-24  Todd Valentic
#               Updated for transport3 / python3
#               Don't run if station is unknown
#
############################################################################

import bz2
import json
import pathlib
import sys

from datatransport import ProcessClient
from datatransport import newstool
from datatransport import NewsPoller
from datatransport import ConfigComponent


class FileGroup(ConfigComponent):
    """File Group"""

    def __init__(self, name, config, parent):
        ConfigComponent.__init__(self, "filegroup", name, config, parent)

        self.news_poller = NewsPoller(self, callback=self.process)

        self.outputpath = self.config.get_path("output.path", ".")
        self.uncompress = self.config.get_boolean("uncompress", False)

    def uncompress_file(self, pathname):
        """Uncompress file"""

        # Only handle bzip2 files at this time

        self.log.info("Uncompressing %s", pathname)

        data = pathname.read_bytes()

        output_pathname = pathname.with_suffix("")

        output_pathname.write_bytes(bz2.decompress(data))

        pathname.unlink()

    def process(self, message):
        """Message handler"""

        if not self.preprocess(message):
            return

        pathnames = newstool.save_files(message, path=self.outputpath)

        for pathname in pathnames:
            self.log.info("Saved %s", pathname)
            if self.uncompress and pathname.endswith("bz2"):
                self.uncompress_file(pathname)

        self.postprocess(message, pathnames)

    # pylint: disable=unused-argument

    def preprocess(self, message):
        """Used by derived classes"""
        return True

    def postprocess(self, message, pathnames):
        """Used by derived classes"""
        return

    def run_step(self):
        self.news_poller.run_step()

class AckFileGroup(FileGroup):
    """Ack Files"""

    def __init__(self, *pos, **kw):
        FileGroup.__init__(self, *pos, **kw)

        ackpath = self.config.get("ack.path", ".")
        ackname = self.config.get("ack.name", "ack-%Y%m%d-%H%M%S.dat")

        self.ack_pathname = pathlib.Path(ackpath, ackname)

    def postprocess(self, message, pathnames):
        """Post process handler"""

        self.wait(1)  # Ensure the time-based ack filenames are unique

        now = self.now()
        serialnum = message["X-Transport-SerialNum"]

        msg = {
            "timestamp": now,
            "pathnames": pathnames,
            "serialnum": serialnum,
            "filegroup": self.name,
        }

        ack_pathname = now.strftime(str(self.ack_pathname))

        ack_pathname.parent.mkdir(parents=True, exist_ok=True)

        contents = json.dumps(msg, default=str)
        ack_pathname.write_text(contents, encoding="utf-8")

        self.log.info("  - serial num: %s", serialnum)
        self.log.info("  - sent ack: %s", ack_pathname.name)


class PollFiles(ProcessClient):
    """File Poller Process Client"""

    def __init__(self, argv, factory=FileGroup):
        ProcessClient.__init__(self, argv)

        station = self.config.get("station")

        if station == "unknown":
            self.abort("Station has not been set yet")

        self.pollrate = self.config.get_rate("pollrate", "5m")
        self.exit_on_error = self.config.get_boolean("exit_on_error", False)
        self.filegroups = self.config.get_components("filegroups", factory=factory)

        self.log.info("Loaded %d file groups:", len(self.filegroups))

        for filegroup in self.filegroups:
            self.log.info("  - %s", filegroup)

    def process(self):
        """Process each file group"""

        self.log.debug("Processing feeds")

        for filegroup in self.filegroups.values():
            if not self.is_running():
                break

            try:
                filegroup.run_step()
            except StopIteration:
                break
            except SystemExit:
                self.exit_event.set()
                break
            except:  # pylint: disable=bare-except
                self.log.exception("Error processing filegroup %s", filegroup.name)
                if self.exit_on_error:
                    self.exit_event.set()

    def main(self):
        """Main application"""

        while self.wait(self.pollrate):
            self.process()

        self.log.info("Finished")


if __name__ == "__main__":
    PollFiles(sys.argv, factory=AckFileGroup).run()
