#!/usr/bin/env python3
"""Victron ModBus Interface"""

##########################################################################
#
#   Victron test 
#
#   2023-08-28  Todd Valentic
#               Initial implementation
#
##########################################################################

import asyncio

from pymodbus import pymodbus_apply_logging_config

from victron import Victron


async def main(*coros):
    """Run tasks"""

    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(coro) for coro in coros]

    return [task.result() for task in tasks]


def test():
    """Test application"""

    pymodbus_apply_logging_config("DEBUG")

    filename = "Field_list-Table_1.csv"
    groups = ["system"]

    victron = Victron(filename, host="127.0.0.1", port=5024)

    meters = [victron]

    coros = [meter.read(groups) for meter in meters]
    results = asyncio.run(main(*coros))

    results = dict(zip(meters, results))
    results = {k: v for k, v in results.items() if v}

    if not results:
        print("No results")
        return

    print(results)

    for meter, result in results.items():
        for group, values in result.items():
            for reg in values:
                print(
                    f"[{group} {reg.address:4} {reg.path}] {reg.value} {reg.unit} {reg.description}"
                )


if __name__ == "__main__":
    test()
