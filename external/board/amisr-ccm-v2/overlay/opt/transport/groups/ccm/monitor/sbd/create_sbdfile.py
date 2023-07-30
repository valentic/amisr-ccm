#!/usr/bin/env python3
"""Create an SDB FILE_UPLOAD Message"""

##########################################################################
#
#   Create a FILE_UPLOAD SBD messsage 
#
#   2019-05-22  Todd Valentic
#               Initial implementation
#
#   2023-07-09  Todd Valentic
#               Updated to python3
#
##########################################################################

import argparse
import bz2
import sys
import struct
import time
import zlib

from pathlib import Path

from sbd_types import MessageType, FileFlags


def chunk(buffer, n):
    """Split buffer"""

    return [buffer[k : k + n] for k in range(0, len(buffer), n)]

# pylint: disable=too-many-locals

def create_message(args):
    """Create an SBD message"""

    input_path = Path(args.input_name)

    try:
        contents = input_path.read_bytes()
    except OSError as e:
        print(f"Problem reading input: {e}")
        return 1

    crc32 = zlib.crc32(contents)
    contents_len = len(contents)

    flags = 0
    if args.execute:
        flags |= FileFlags.EXECUTE
    if args.remove:
        flags |= FileFlags.REMOVE

    compressed_contents = bz2.compress(contents)
    if len(compressed_contents) < len(contents):
        flags |= FileFlags.COMPRESSED
        contents = compressed_contents

    destname = args.filename or args.input_name
    destname = destname.encode('ascii') 

    meta_fmt = f"!BiB{len(destname)}s"
    meta = struct.pack(meta_fmt, flags, crc32, len(destname), destname)

    contents = meta + contents

    # MT payloads are limited to 270 bytes for 960X SBD modems
    # Split into 250-byte blocks (to leave room for header)

    blocks = chunk(contents, 250)
    time.sleep(1)  # Ensure we have a new timestamp
    sernum = int(time.time())

    total_blocks = len(blocks)
    msg_type = MesssageType.FILE_UPLOAD 
    msg_version = 0

    for index, block in enumerate(blocks):
        header = struct.pack(
            "!2BI2B", msg_type, msg_version, sernum, index, total_blocks
        )

        output_name = args.output or input_path.stem
        output_path = Path(f"{output_name}_{index:03d}.sbd")
        output_path.write_bytes(header + block)

    print(f"Serial num:  {sernum}")
    print(f"Total parts: {total_blocks}")
    print(f"Payload len: {contents_len}")
    print(f"CRC32:       {crc32}")
    print(f"Execute?     {bool(flags & FileFlags.EXECUTE)}")
    print(f"Compressed?  {bool(flags & FileFlags.COMPRESSED)}")
    print(f"Remove?      {bool(flags & FileFlags.REMOVE)}")

    return 0


def main():
    """Main application"""

    parser = argparse.ArgumentParser(description="Create SBD file messages")

    parser.add_argument("-x", "--execute", action="store_true", help="Set execute flag")
    parser.add_argument("-r", "--remove", action="store_true", help="Set remove flag")
    parser.add_argument("-f", "--filename", help="Embedded filename")
    parser.add_argument("-o", "--output", help="Output filename")
    parser.add_argument("-s", "--sernum", help="Serial number")

    parser.add_argument("input_name")

    args = parser.parse_args()

    return_code = create_message(args)

    sys.exit(return_code)

if __name__ == "__main__":
    main()
