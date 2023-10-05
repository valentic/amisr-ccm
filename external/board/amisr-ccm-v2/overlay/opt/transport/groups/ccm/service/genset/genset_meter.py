#!/usr/bin/env python3
"""Genset ModBus Interface"""

##########################################################################
#
#   Genset Modbus Interface
#
#   Read the comap genset controller state using modbus (asynchoronous)
#
#   2023-08-03  Todd Valentic
#               Initial implementation
#
#   2023-08-24  Todd Valentic
#               Add retry in read_register
#
#   2023-08-28  Todd Valentic
#               Convert to use ModbusMeter base class
#
##########################################################################

from modbus_meter import ModbusMeter
from genset_regmap import GensetRegisters


class Genset(ModbusMeter):
    """Genset ComAp Meter"""

    def __init__(self, filename, host, access_code=None, **kwarg):
        registers = GensetRegisters(filename)
        ModbusMeter.__init__(self, registers, host, access_code=None, **kwarg)
        self.access_code = int(access_code)

    async def authenticate(self, client):
        """Write access code"""

        tcp_access_addr = 46339 - 40000 - 1

        rr = await client.write_register(
            tcp_access_addr, self.access_code, slave=1
        )

        if rr.isError():
            raise OSError(f"Writing access code: {rr}")

    def decode(self, decoder, reg):
        """Decode raw register"""

        if reg.type.startswith("Binary") and reg.words == 1:
            value = decoder.decode_16bit_uint()
        elif reg.type.startswith("Binary") and reg.words == 2:
            value = decoder.decode_32bit_uint()
        elif reg.type.startswith("Integer") and reg.words == 1:
            value = decoder.decode_16bit_int()
        elif reg.type.startswith("Unsigned") and reg.words == 1:
            value = decoder.decode_16bit_uint()
        elif reg.type.startswith("Unsigned") and reg.words == 2:
            value = decoder.decode_32bit_uint()
        elif reg.type.startswith("Integer") and reg.words == 2:
            value = decoder.decode_32bit_int()
        elif reg.type.startswith("List") and reg.words == 1:
            value = decoder.decode_16bit_uint()
        elif reg.type.startswith("List") and reg.words == 2:
            value = decoder.decode_32bit_uint()
        elif reg.type.startswith("String"):
            value = decoder.decode_string(reg.words * 2).decode("ascii")
        elif reg.type.startswith("Timer"):
            value = decoder.decode_64bit_int()
        elif reg.type.startswith("Char"):
            value = decoder.decode_string(1).decode("ascii")[0]
            if value == "\x00":
                value = ""
        else:
            raise ValueError(f"Unknown type: {reg.type}")

        return value
