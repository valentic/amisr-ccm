#!/usr/bin/env python3
"""Genset ModBus Interface"""

##########################################################################
#
#   Genset Modbus Interface
#
#   Read the comap genset controller state using modbus (synchoronous)
#
#   2023-08-03  Todd Valentic
#               Initial implementation
#
#   2023-08-24  Todd Valentic
#               Add retry in read_register
#
##########################################################################

import logging
import time

from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder

from genset_regmap import GensetRegisters

MAX_RETRIES=3
RETRY_WAIT=10

class Genset:
    """Read Genset Status"""

    def __init__(self, filename, host, port=502, unit=1, access_code=None):
        self.registers = GensetRegisters(filename)
        self.client = ModbusTcpClient(host, port=port)
        self.unit = unit
        self.access_code = int(access_code)

    def send_access_code(self):

        tcp_access_addr = 46339 - 40000 - 1

        rr = self.client.write_register(tcp_access_addr, self.access_code, slave=1)

        if rr.isError():
            raise OSError('Writing access code: %s' % rr)

    def read(self, group_name):
        """Read status for a group"""

        for retry in range(MAX_RETRIES): 
            if self.client.connect():
                if retry: 
                    logging.info("Connection established")
                break

            logging.warning("Retry #%s", retry)
            time.sleep(5)

        if not self.client.connected:
            raise OSError('Failed to connect')

        if self.access_code:
            self.send_access_code()

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

        for retry in range(MAX_RETRIES): 
            data = self.client.read_holding_registers(addr, num_words, slave=self.unit)

            if not data.isError():
                break

            logging.warning("Retry #%s for addr %s", retry, addr)
            time.sleep(5)

        if data.isError():
            raise OSError('Exception: %s' % data)

        results = []
        decoder = BinaryPayloadDecoder.fromRegisters(data.registers, byteorder=">")

        for reg in block:
            if reg.type.startswith("Binary") and reg.words==1:
                value = decoder.decode_16bit_uint()
            elif reg.type.startswith("Binary") and reg.words==2:
                value = decoder.decode_32bit_uint()
            elif reg.type.startswith("Integer") and reg.words==1:
                value = decoder.decode_16bit_int()
            elif reg.type.startswith("Unsigned") and reg.words==1:
                value = decoder.decode_16bit_uint()
            elif reg.type.startswith("Unsigned") and reg.words==2:
                value = decoder.decode_32bit_uint()
            elif reg.type.startswith("Integer") and reg.words==2:
                value = decoder.decode_32bit_int()
            elif reg.type.startswith("List") and reg.words==1:
                value = decoder.decode_16bit_uint()
            elif reg.type.startswith("List") and reg.words==2:
                value = decoder.decode_32bit_uint()
            elif reg.type.startswith("String"):
                value = decoder.decode_string(reg.words*2).decode('ascii')
            elif reg.type.startswith("Timer"):
                value = decoder.decode_64bit_int()
            elif reg.type.startswith("Char"):
                value = decoder.decode_string(1).decode('ascii')[0]
                if value == '\x00':
                    value = ''
            else:
                raise ValueError("Unknown type: %s" % reg.type)

            reg.set(value)

            results.append(reg)

        return results


def test():
    """Test application"""

    #logging.basicConfig(level=logging.DEBUG)

    # SGM 192.168.10.112

    filename = "20220127_G3_register_map.TXT"
    access_code = 2747

    #genset = Genset(filename, host="localhost", port=5022, access_code=access_code)
    genset = Genset(filename, host="genset-sgm", port=502, access_code=access_code)

    groups = [
        'ECU', 'Gener_values', 'Bus_values', 'Analog_CU', 
        'Statistics', 'Bin_inputs_CU', 'Binary_Inputs'
    ]

    results = []

    for group in groups:
        results.extend(genset.read(group))

    for reg in results:
        print(f"[{reg.register:5} {reg.path}] {reg.value} {reg.unit} {reg.description}")


if __name__ == "__main__":
    test()
