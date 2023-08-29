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
        self.client = AsyncModbusTcpClient(host, **kwargs) 
        self.unit = unit
        self.byteorder = byteorder

    async def authenticate(self):
        """Handle authenticaion on devices that need it"""
        pass

    async def read(self, group_names):
        """Read status for a group"""

        await self.client.connect()

        if not self.client.connected:
            raise OSError('Failed to connect')

        await self.authenticate()

        results = {} 

        try:
            for group_name in group_names:
                data = []
                for block in self.registers.get_register_blocks(group_name):
                    values = await self.read_registers(block)
                    data.extend(values)
                results[group_name] = data
        finally:
            self.client.close()

        return results

    async def read_registers(self, block):
        """Read holding registers"""

        addr = block[0].address
        num_words = sum(reg.words for reg in block)

        data = await self.client.read_holding_registers(addr, num_words, slave=self.unit)

        if data.isError():
            raise OSError('Exception: %s' % data)

        decoder = BinaryPayloadDecoder.fromRegisters(data.registers, byteorder=self.byteorder)

        results = []

        for reg in block:
            value = self.decode(decoder, reg)
            reg.set(value)
            results.append(reg)

        return results

