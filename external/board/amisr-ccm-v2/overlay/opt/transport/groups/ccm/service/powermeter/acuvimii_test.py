#!/usr/bin/env python3
"""Acuvim test"""

##########################################################################
#
#   Acuvim II test
#
#   2023-08-28  Todd Valentic
#               Initial implementation
#
##########################################################################

import asyncio

from pymodbus import pymodbus_apply_logging_config

from acuvimii import AcuvimII


async def main(*coros):
    """Run tasks"""

    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(coro) for coro in coros]

    return [task.result() for task in tasks]


def test():
    """Test application"""

    pymodbus_apply_logging_config("DEBUG")

    filename = "rmap.json"
    groups = ["sys", "basic"]

    acuvim = AcuvimII(filename, host="localhost", port=5021)

    meters = [acuvim.read(groups)]

    results = asyncio.run(main(meters))

    for result in results:
        for group in result:
            print(f"---- {group} ----")
            results = acuvim.read(group)

            for reg in results:
                print(
                    f"[{reg.address:4X} {reg.path}] {reg.value} {reg.unit} {reg.description}"
                )


if __name__ == "__main__":
    test()
