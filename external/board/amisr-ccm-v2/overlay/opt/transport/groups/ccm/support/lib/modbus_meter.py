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
#   2023-10-03  Todd Valentic
#               Use context manager for connection
#               Add virtual registers
#
##########################################################################

import asyncio
import logging
import time

from contextlib import asynccontextmanager
from functools import partial

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
        self.controls = {}

    def add_control(self, name, func, *args, **kwargs):
        self.controls[name] = partial(func, *args, **kwargs)

    def list_controls(self):
        """List controls"""

        return list(self.controls)

    def list_groups(self):
        """List of groups"""

        return self.registers.list_groups()

    def list_registers(self):
        """List registers"""

        return self.registers.list_registers()

    def list_register(self, path):
        """Return register values at path"""
        
        return self.registers.get_register(path)

    @asynccontextmanager
    async def modbus_connect(self, *args, **kwargs):
        """Managed connection"""

        client = AsyncModbusTcpClient(*args, **kwargs) 

        await client.connect()

        if not client.connected:
            raise IOError('Failed to connect')

        await self.access(client)

        try:
            yield client
        finally:
            client.close()

    async def access(self, _client):
        """Handle access code on devices that need it"""

    async def authenticate(self, _client):
        """Handle authenticaion on devices that need it"""

    async def read_register_path(self, path):
        """Read a register at path"""

        async with self.modbus_connect(self.host, **self.kwargs) as client:
            block = self.registers.get_register_block(path)
            data = await self.read_block(client, block)

        return data[0].value

    async def read_register_addr(self, addr, num_words):
        """Read registers at addr"""

        async with self.modbus_connect(self.host, **self.kwargs) as client:
            data = await client.read_holding_registers(addr, count=num_words, slave=self.unit)
            if data.isError():
                raise OSError('Exception: %s' % data)

        decoder = BinaryPayloadDecoder.fromRegisters(data.registers, byteorder=self.byteorder)

        return [decoder.decode_16bit_uint() for _ in range(num_words)]

    async def write_register_path(self, path, *values):
        """Write to single register"""

        addr = self.registers.get_register(path).address

        return await self.write_register_addr(addr, *values)

    async def write_register_addr(self, addr, *values):
        """Write to single register"""

        async with self.modbus_connect(self.host, **self.kwargs) as client:
            await self.authenticate(client)
            if len(values) > 1:
                await client.write_registers(addr, values, slave=self.unit)
            else:
                await client.write_register(addr, values[0], slave=self.unit)

        return True

    async def read_group(self, group_name):
        """Read status for a group"""

        async with self.modbus_connect(self.host, **self.kwargs) as client:
            data = []
            for block in self.registers.get_register_blocks(group_name):
                values = await self.read_block(client, block)
                data.extend(values)

        return data 

    async def read_groups(self, group_names):
        """Read multiple groups"""

        async with self.modbus_connect(self.host, **self.kwargs) as client:
            results = {} 

            for group_name in group_names:
                data = []
                for block in self.registers.get_register_blocks(group_name):
                    values = await self.read_block(client, block)
                    data.extend(values)
                results[group_name] = data

        return results

    async def read_virtual(self, _state):
        """Compute virtual register values from existing data"""

        return None

    async def read_block(self, client, block):
        """Read holding registers in a block"""

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

    async def control(self, cmd):
        """Run control command"""

        return await self.controls[cmd]()


