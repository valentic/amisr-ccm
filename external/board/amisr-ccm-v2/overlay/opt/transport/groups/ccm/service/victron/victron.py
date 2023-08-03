#!/usr/bin/env python3
"""Victron ModBus Interface"""

##########################################################################
#
#   Victron Modbus Interface
#
#   Read the victron charge controller state using modbus (synchoronous)
#
#   2023-08-01  Todd Valentic
#               Initial implementation
#
##########################################################################

import logging

from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder

from victron_regmap import VictronRegisters

# logging.basicConfig(level=logging.DEBUG)


class Victron:
    """Read Victron Status"""

    def __init__(self, filename, host, port=502, unit=100):
        self.registers = VictronRegisters(filename)
        self.client = ModbusTcpClient(host, port=port)
        self.unit = unit

    def read(self, group_name):
        """Read status for a group"""

        self.client.connect()

        results = []

        for block in self.registers.get_register_blocks(group_name):
            values = self.read_registers(block)
            results.extend(values)

        self.client.close()

        return results

    def read_registers(self, block):
        """Read holding registers"""

        addr = block[0].address
        num_words = sum(reg.words for reg in block)

        data = self.client.read_holding_registers(addr, num_words, slave=self.unit)

        if data.isError():
            raise IOError('Exception: %s' % data)

        results = []
        decoder = BinaryPayloadDecoder.fromRegisters(data.registers, byteorder=">")

        for reg in block:
            if reg.type.startswith("string"):
                value = str(decoder.decode_string(reg.words * 2), 'utf-8')
            elif reg.type == "uint16":
                value = decoder.decode_16bit_uint()
            elif reg.type == "int16":
                value = decoder.decode_16bit_int()
            elif reg.type == "uint32":
                value = decoder.decode_32bit_uint()
            elif reg.type == "int32":
                value = decoder.decode_32bit_int()

            reg.set(value)

            results.append(reg)

        return results


def test():
    """Test application"""

    logging.basicConfig(level=logging.DEBUG)

    filename = "Field_list-Table_1.csv"

    victron = Victron(filename, host="127.0.0.1", port=5020)
    results = victron.read("system")

    for reg in results:
        print(f"[{reg.address:4} {reg.path}] {reg.value} {reg.unit} {reg.description}")


if __name__ == "__main__":
    test()
