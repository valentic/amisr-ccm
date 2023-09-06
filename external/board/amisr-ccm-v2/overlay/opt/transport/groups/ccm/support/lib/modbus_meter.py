#!/usr/bin/env python3
"""ModBus Meter Interface"""

##########################################################################
#
#   Modbus Meter Interface Base Class
#
#   Base class for async modbus meters.  
#
#   2023-08-28  Todd Valentic
#               Initial implementation
#
#   2023-09-05  Todd Valentic
#               Need to create client instance each time, otherwise
#                   it uses a loop that has been closed
#
##########################################################################

import asyncio
import logging
import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder

class ModbusMeter:
    """Read Genset Status"""

    def __init__(self, registers, host, unit=1, byteorder=">", **kwargs):
        self.registers = registers 
        self.unit = unit
        self.byteorder = byteorder
        self.host = host
        self.kwargs = kwargs

    async def authenticate(self, _client):
        """Handle authenticaion on devices that need it"""
        pass

    async def read(self, group_names):
        """Read status for a group"""

        client = AsyncModbusTcpClient(self.host, **self.kwargs) 

        await client.connect()

        if not client.connected:
            raise OSError('Failed to connect')

        await self.authenticate(client)

        results = {} 

        try:
            for group_name in group_names:
                data = []
                for block in self.registers.get_register_blocks(group_name):
                    values = await self.read_registers(client, block)
                    data.extend(values)
                results[group_name] = data
        finally:
            client.close()

        return results

    async def read_registers(self, client, block):
        """Read holding registers"""

        addr = block[0].address
        num_words = sum(reg.words for reg in block)

        data = await client.read_holding_registers(addr, num_words, slave=self.unit)

        if data.isError():
            raise OSError('Exception: %s' % data)

        decoder = BinaryPayloadDecoder.fromRegisters(data.registers, byteorder=self.byteorder)

        results = []

        for reg in block:
            value = self.decode(decoder, reg)
            reg.set(value)
            results.append(reg)

        return results

