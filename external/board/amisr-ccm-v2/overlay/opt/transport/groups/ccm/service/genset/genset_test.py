#!/usr/bin/env python
"""Test genset"""

##########################################################################
#
#   Genset test
#
#   2023-08-28  Todd Valentic
#               Initial implementation
#
##########################################################################

import asyncio

from pymodbus import pymodbus_apply_logging_config

from genset import Genset


async def main(*meters):
    """Run tasks"""

    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(meter) for meter in meters]

    return [task.result() for task in tasks]


def test():
    """Test application"""

    pymodbus_apply_logging_config("DEBUG")

    # SGM 192.168.10.112

    filename = "20230816_G3.TXT"
    access_code = 2747
    host = "genset-sgm"
    port = 502

    genset = Genset(filename, host=host, port=port, access_code=access_code)

    groups = [
        "ECU",
        "Gener_values",
        "Bus_values",
        "Analog_CU",
        "Statistics",
        "Bin_inputs_CU",
        "Binary_Inputs",
    ]

    results = asyncio.run(main([genset.read(groups)]))

    for meter in results:
        for reg in meter.values():
            print(
                f"[{reg.register:5} {reg.path}] {reg.value} {reg.unit} {reg.description}"
            )


if __name__ == "__main__":
    test()
