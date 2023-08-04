#!/usr/bin/env python3
"""Acuvim II ModBus Interface"""

##########################################################################
#
#   Acuvim II Modbus Interface
#
#   Read the Acuvim II power meter state using modbus (synchoronous)
#
#   2023-08-02  Todd Valentic
#               Initial implementation
#
##########################################################################

from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder

from acuvimii_regmap import AcuvimIIRegisters


class AcuvimII:
    """Read Acuvim II Status"""

    def __init__(self, filename, host, port=502, unit=1):
        self.registers = AcuvimIIRegisters(filename)
        self.client = ModbusTcpClient(host, port=port)
        self.unit = unit

    def read(self, group_name):
        """Read status for a group"""

        self.client.connect()

        results = []

        try:
            for block in self.registers.get_register_blocks(group_name):
                values = self.read_registers(block)
                results.extend(values)
        finally:
            self.client.close()

        return results

    def read_registers(self, block):
        """Read holding registers"""

        addr = block[0].address
        num_words = sum(reg.words for reg in block)

        data = self.client.read_holding_registers(addr, num_words, slave=self.unit)

        if data.isError():
            raise IOError(f"{data}")

        results = []
        decoder = BinaryPayloadDecoder.fromRegisters(data.registers, byteorder=">")

        for reg in block:
            if reg.type == "word":
                value = decoder.decode_16bit_uint()
            elif reg.type == "int":
                value = decoder.decode_16bit_int()
            elif reg.type == "dword":
                value = decoder.decode_32bit_uint()
            elif reg.type == "float":
                value = decoder.decode_32bit_float()

            reg.set(value)

            results.append(reg)

        return results


def test():
    """Test application"""

    # import logging
    # logging.basicConfig(level=logging.DEBUG)

    filename = "rmap.json"

    acuvim = AcuvimII(filename, host="localhost", port=5021)

    groups = ["sys", "basic"]

    for group in groups:
        print(f"---- {group} ----")
        results = acuvim.read(group)

        for reg in results:
            print(
                f"[{reg.address:4X} {reg.path}] {reg.value} {reg.unit} {reg.description}"
            )


if __name__ == "__main__":
    test()
