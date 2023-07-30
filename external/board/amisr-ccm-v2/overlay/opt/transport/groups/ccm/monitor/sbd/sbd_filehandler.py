#!/usr/bin/env python3
"""Handle inbound SBD FILE messages"""

# pylint: disable=bare-except, too-many-locals, too-many-statements

##########################################################################
#
#   Handle inbound SBD FILE type messages
#
#   2019-05-21  Todd Valentic
#               Initial implementation
#
#   2019-07-24  Todd Valentic
#               Limit status to 0-255 (one byte)
#
#   2023-07-10  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import bz2
import subprocess
import json
import glob
import os
import struct
import sys
import time
import zlib

from pathlib import Path

from datatransport.utilities import remove_file

from sbd_types import FileFlags


def make_ack(sernum, contents_ok, process_ok, result_code):
    """Create ACK message"""
    fmt = "!BIIBBB"
    ver = 1
    timestamp = time.time()
    return struct.pack(fmt, ver, timestamp, sernum, contents_ok, process_ok, result_code)


class SBDFileHandler:
    """Handle SBD File messages"""

    def __init__(self, log):
        self.log = log

    def process_contents(self, meta, contents):
        """Save, remove or execute file contents"""

        status = 0

        filename = Path(meta["filename"])

        filename.parent.mkdir(parents=True, exist_ok=True)

        with filename.open("wb") as destfile:
            destfile.write(contents)
            destfile.flush()
            os.fsync(destfile.fileno())

        if meta["flags"] & FileFlags.EXECUTE:
            filename.chmod(0o775)
            cmd = filename.absolute()
            status, output = subprocess.getstatusoutput(cmd)

            if status < 0 or status > 255:
                status = 255

            self.log.info("  - file executed, result status %d", status)
            self.log.info("  - output: %s", output)

        if meta["flags"] & FileFlags.REMOVE:
            self.log.info("  - remove %s", filename)
            filename.unlink()

        return status

    def process(self, payload):
        """Dispatch processing based on version of command"""

        version = struct.unpack_from("!B", payload)[0]

        if version == 0:
            return self.process_version_0(payload)

        return None

    def process_version_0(self, payload):
        """Version 0 processing"""

        header_fmt = "!BI2B"
        header_len = struct.calcsize(header_fmt)

        _version, sernum, part, total = struct.unpack_from(header_fmt, payload)

        payload = payload[header_len:]

        meta_filename = Path(f"{sernum}.meta")

        if part == 0:
            meta_fmt = "!BiB"
            meta_len = struct.calcsize(meta_fmt)

            flags, crc32, filename_len = struct.unpack_from(meta_fmt, payload)

            filename_fmt = f"!{filename_len}s"
            filename = struct.unpack_from(filename_fmt, payload, offset=meta_len)[0]

            payload = payload[meta_len + filename_len :]

            meta = {"flags": flags, "crc32": crc32, "filename": filename}

            meta_filename.write_text(json.dumps(meta), encoding='utf-8')

            # Remove any older parts from previous try (if any)
            remove_file(glob.glob(f"{sernum}-*.part"))

        part_filename = Path("f{sernum}-%{part:03d}-{total}.part")
        part_filename.write_bytes(payload)

        # Do we have all of the parts?

        parts = glob.glob(f"{sernum}-*.part")

        if len(parts) == total:
            meta = dict(json.loads(meta_filename.read_text('utf-8')))

            self.log.info("New file: %s", meta_filename)
            self.log.info("  - serial num: %s", sernum)
            self.log.info("  - parts: %s", total)
            self.log.info("  - flags: 0x%x", meta["flags"])

            contents = ""

            for filepart in sorted(parts):
                contents += Path(filepart).read_bytes()

            self.log.info("  - len: %d", len(contents))

            if meta["flags"] & FileFlags.COMPRESSED:
                self.log.info("  - uncompressing")
                try:
                    contents = bz2.decompress(contents)
                except:
                    self.log.error("  - failed to uncompress")
                    contents = ""

            if zlib.crc32(contents) != meta["crc32"]:
                self.log.error(
                    "  - checksum mismatch. expected %s, got %s",
                    meta["crc32"], zlib.crc32(contents)
                )
                contents = ""

            process_ok = False
            result_code = 0

            if contents:
                try:
                    result_code = self.process_contents(meta, contents)
                    process_ok = True
                except:
                    self.log.exception("Failed to process contents")
                    process_ok = False

            remove_file(parts)
            meta_filename.unlink()

            contents_ok = len(contents) > 0
            ack = make_ack(sernum, contents_ok, process_ok, result_code)

            return ack

        return None

def test():
    """Testing"""

    # pylint: disable=import-outside-toplevel

    import logging

    logging.basicConfig(level=logging.INFO)

    handler = SBDFileHandler(logging)

    for filename in sys.argv[1:]:
        logging.debug(filename)
        payload = Path(filename).read_bytes()
        handler.process(payload[1:])

if __name__ == "__main__":
    test()
