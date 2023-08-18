#!/usr/bin/env python3
"""Post Files"""

############################################################################
#
#   Post new files
#
#   2019-06-27  Todd Valentic
#               Initial implementation. Based on PostDataFiles.py
#
#   2019-07-23  Todd Valentic
#               Filter out names starting with '.' (these are partial files)
#
#   2019-08-03  Todd Valentic
#               Add time parsing for vmti names
#
#   2021-07-16  Todd Valentic
#               Make filename time parsing optional
#
#   2021-07-17  Todd Valentic
#               Add serialnum option
#               Use path, filename, pathname nomenclature
#
#   2023-07-24  Todd Valentic
#               Updated to transport3 / python3
#               Abort if station hasn't been set ("unknown")
#
############################################################################

import bz2
import datetime
import os
import pathlib
import re
import subprocess
import sys
import time
import uuid

import pytz

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import ConfigComponent
from datatransport.utilities import PatternTemplate, remove_file, size_desc


class FileGroup(ConfigComponent):
    """File Group"""

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, "filegroup", *p, **kw)

        station = self.config.get("station")

        if station == "unknown":
            self.abort("Station has not been set yet")

        self.start_path = self.config.get_path("start.path", ".")
        self.match_paths = self.config.get_list("match.paths", "*")
        self.match_names = self.config.get_list("match.names", "*")
        self.compress = self.config.get_boolean("compress", False)
        self.remove_files = self.config.get_boolean("remove_files", False)
        self.include_last = self.config.get_boolean("include_last", True)
        self.start_current = self.config.get_boolean("start_current", False)
        self.max_files = self.config.get_int("max_files")
        self.enable_parse_time = self.config.get_boolean("parse_time", True)
        self.enable_serial_num = self.config.get_boolean("add_serialnum", False)

        self.replace_path = PatternTemplate("path", "/")

        self.newsgroup_template = self.config.get("post.newsgroup.template")

        self.posters = {}
        self.time_filename = pathlib.Path(f"{self.name}.timestamp")

        if not self.time_filename.exists():
            # Default to sometime long ago
            self.time_filename.write_text("0", encoding="utf-8")
            t = time.mktime((1975, 1, 1, 0, 0, 0, 0, 0, 0))
            os.utime(self.time_filename, (t, t))

        if self.start_current:
            os.utime(self.time_filename, None)

        self.log.info("Watching for files in %s", self.start_path)
        self.log.info("match paths %s", " ".join(self.match_paths))
        self.log.info("match names %s", " ".join(self.match_names))

    def parse_time(self, filename):
        """Parse timestamp from filename"""

        # Standard format - 20190802-200555C00SEQ01.ntf
        # Log format - hs-07-20190803-165804.log
        # VMTI format - vmti_08-02-2019_UTC20-04-55_0000_00.4607

        regexs = [
            (r"\d{8}.\d{6}", "%Y%m%d-%H%M%S"),
            (r"\d{2}-\d{2}-\d{4}_UTC\d{2}-\d{2}-\d{2}", "%m-%d-%Y-UTC%H-%M-%S"),
        ]

        timestamp = None

        for regex, timefmt in regexs:
            try:
                timestr = re.findall(regex, filename)[0]
                timestr = timestr.replace("_", "-")
                timestamp = datetime.datetime.strptime(timestr, timefmt)
                timestamp = timestamp.replace(tzinfo=pytz.utc)
                break
            except Exception: # pylint: disable=broad-exception-caught
                pass

        if timestamp is None:
            self.log.warn("Unable to parse timestamp from filename: %s", filename)

        return timestamp

    def post(self, pathname):
        """Post file"""

        if self.enable_parse_time:
            timestamp = self.parse_time(os.path.basename(pathname))
        else:
            timestamp = None

        newsgroup = self.replace_path(self.newsgroup_template, str(pathname))
        filesize = os.path.getsize(pathname)

        self.log.info(
            "  - posting %s (%s) to %s", pathname, size_desc(filesize), newsgroup
        )

        if not newsgroup in self.posters:
            self.config.set("post.newsgroup", newsgroup)
            self.posters[newsgroup] = NewsPoster(self, prefix="post")
            self.log.info('host: %s', self.posters[newsgroup].server_host)
            self.log.info('port: %s', self.posters[newsgroup].server_port)
            self.log.info('enabled: %s', self.posters[newsgroup].enabled)


        headers = {}

        if self.enable_serial_num:
            headers["X-Transport-SerialNum"] = str(uuid.uuid4())

        self.posters[newsgroup].post([pathname], date=timestamp, headers=headers)

        self.log.info('post done')

        self.wait(2)

    def process_file(self, pathname):
        """Process file"""

        self.log.info("Processing %s", pathname)

        bzipext = ".bz2"
        is_compressed = pathname.suffix == bzipext
        zipname = pathlib.Path(pathname.name+bzipext)

        if self.compress and not is_compressed:
            self.log.debug("  - compressing file")
            data = pathname.read_bytes()
            zipname.write_bytes(bz2.compress(data))

            orgsize = os.path.getsize(pathname)
            zipsize = os.path.getsize(zipname)

            if orgsize > 0:
                zippct = (zipsize / float(orgsize)) * 100
            else:
                zippct = 0

            self.log.info(
                "  - %s -> %s (%d%%)", 
                size_desc(orgsize), size_desc(zipsize), zippct
            )

            postfile = zipname

        else:
            postfile = pathname

        self.post(postfile)

        # Cleanup files

        remove_file(zipname)

        if self.remove_files:
            remove_file(pathname)

    def join_list(self, name, parts):
        """Create an or-ed parameter list"""

        result = [f'-{name} "{part}"' for part in parts]
        result = " -o ".join(result)
        result = f"\\( {result} \\)" 

        return result

    def find_files(self):
        """Search for files to post"""

        if not self.start_path.exists():
            return []

        names = self.join_list("name", self.match_names)
        paths = self.join_list("path", self.match_paths)

        cmd = (
            f"find {self.start_path} -newer {self.time_filename} "
            f"-type f {paths} {names} -print" 
        )

        self.log.debug("cmd=%s", cmd)

        status, output = subprocess.getstatusoutput(cmd)

        if status != 0:
            self.log.error('Problem finding files:')
            self.log.error('cmd=%s', cmd)
            self.log.error('status=%s', status)
            self.log.error('output=%s', output)
            return []

        self.log.debug("status=%s", status)
        self.log.debug("output='%s'", output)

        filelist = []

        for line in output.split('\n'):
            filename = pathlib.Path(line)
            if not filename.name or filename.name.startswith("."):
                continue
            filelist.append(filename)

        filelist.sort()

        if not self.include_last:
            # don't include the current file
            filelist = filelist[0:-1]

        if self.max_files:
            # keep only the last N files
            if self.remove_files:
                remove_file(filelist[:-self.max_files])

            filelist = filelist[-self.max_files :]

        return filelist

    def process(self):
        """Process handler"""

        filenames = self.find_files()
        self.log.debug("Polling - found %d new files.", len(filenames))

        for filename in filenames:
            if not self.is_running():
                break

            timestamp = os.path.getmtime(filename)
            self.process_file(filename)
            os.utime(self.time_filename, (timestamp, timestamp))


class PostFiles(ProcessClient):
    """Post Files Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.pollrate = self.config.get_rate("pollrate", "5:00")
        self.exit_on_error = self.config.get_boolean("exit_on_error", False)

        self.filegroups = self.config.get_components("filegroups", factory=FileGroup)

    def preprocess(self):
        """Run before processing"""
        return

    def postprocess(self):
        """Run after processing"""

        return

    def process(self):
        """Process file groups"""

        self.preprocess()

        for filegroup in self.filegroups.values():
            try:
                filegroup.process()
            except SystemExit:
                self.stop()
            except Exception as e: # pylint: disable=broad-exception-caught
                if self.exit_on_error:
                    self.log.exception("Problem processing filegroup %s", filegroup.name)
                    self.stop()
                else:
                    self.log.error("Problem processing filegroup %s: %s", filegroup.name, e)

            if not self.is_running():
                break

        self.postprocess()

    def main(self):
        """Main applications"""

        while self.wait(self.pollrate):
            try:
                self.process()
            except SystemExit:
                break
            except Exception: # pylint: disable=broad-exception-caught
                self.log.exception("Problem detected")
                if self.exit_on_error:
                    break

        self.log.info("Finished")


if __name__ == "__main__":
    PostFiles(sys.argv).run()
