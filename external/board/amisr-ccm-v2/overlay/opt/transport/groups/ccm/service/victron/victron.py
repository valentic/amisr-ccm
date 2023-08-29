#!/usr/bin/env python3
"""Victron ModBus Interface"""

##########################################################################
#
#   Victron Modbus Interface
#
#   Read the victron charge controller state using modbus (asynchoronous)
#
#   2023-08-01  Todd Valentic
#               Initial implementation
#
#   2023-08-25  Todd Valentic
#               Convert to use ModbusMeter
#
##########################################################################

from modbus_meter import ModbusMeter
from victron_regmap import VictronRegisters


class Victron(ModbusMeter):
    """Victron Charge Controller Meter"""

    def __init__(self, filename, host, unit=100, **kwargs):
        registers = VictronRegisters(filename)
        ModbusMeter.__init__(self, registers, host, unit=unit, **kwargs)

    def decode(self, decoder, reg):
        """Decode raw register"""

        if reg.type.startswith("string"):
            value = str(decoder.decode_string(reg.words * 2), "utf-8")
        elif reg.type == "uint16":
            value = decoder.decode_16bit_uint()
        elif reg.type == "int16":
            value = decoder.decode_16bit_int()
        elif reg.type == "uint32":
            value = decoder.decode_32bit_uint()
        elif reg.type == "int32":
            value = decoder.decode_32bit_int()
        else:
            raise ValueError(f"Unknown type: {reg.type}")

        return value
