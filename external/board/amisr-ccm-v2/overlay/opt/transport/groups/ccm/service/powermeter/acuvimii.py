#!/usr/bin/env python3
"""Acuvim II ModBus Interface"""

##########################################################################
#
#   Acuvim II Modbus Interface
#
#   Read the Acuvim II power meter state using modbus (asynchoronous)
#
#   2023-08-02  Todd Valentic
#               Initial implementation
#
#   2023-08-28  Todd Valentic
#               Convert to use ModbusMeter base class
#
##########################################################################

from modbus_meter import ModbusMeter
from acuvimii_regmap import AcuvimIIRegisters


class AcuvimII(ModbusMeter):
    """Read Acuvim II Status"""

    def __init__(self, filename, host, **kwargs):
        registers = AcuvimIIRegisters(filename)
        ModbusMeter.__init__(self, registers, host, **kwargs)

    def decode(self, decoder, reg):
        """Decode raw register"""

        if reg.type == "word":
            value = decoder.decode_16bit_uint()
        elif reg.type == "int":
            value = decoder.decode_16bit_int()
        elif reg.type == "dword":
            value = decoder.decode_32bit_uint()
        elif reg.type == "float":
            value = decoder.decode_32bit_float()
        else:
            raise ValueError(f"Unknown type: {reg.type}")

        return value
