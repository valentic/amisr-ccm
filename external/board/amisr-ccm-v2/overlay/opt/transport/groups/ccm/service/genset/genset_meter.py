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
#               Add retry in read_register_path
#
#   2023-08-28  Todd Valentic
#               Convert to use ModbusMeter base class
#
##########################################################################

import asyncio
import datetime

from dataclasses import dataclass
from functools import partial

from modbus_meter import ModbusMeter
from genset_regmap import GensetRegisters
from bitlib import set_bit, clear_bit, get_bit, get_normalized_bit, bcd_decode

MODBUSSW1 = 46337 - 40001
MODBUSCMD = 46359 - 40001

@dataclass
class StatusBit:
    path: str 
    bit: int

feeder_breaker_state = {
    "F1": StatusBit("/Bin_inputs_CU/BIN", 5),
    "F2": StatusBit("/Bin_inputs_CU/BIN", 6),
    "F3": StatusBit("/Binary_Inputs/BIN-1", 4),
}

class GensetMeter(ModbusMeter):
    """Genset ComAp Meter"""

    def __init__(self, filename, host, **kwargs):
        registers = GensetRegisters(filename)
        ModbusMeter.__init__(self, registers, host, **kwargs)
        self.access_code = int(kwargs.pop("access_code", 0))
        self.user_code = int(kwargs.pop("user_code", 0)) 
        self.pass_code = int(kwargs.pop("pass_code", self.access_code))

        cmdreg = partial(self.write_register_addr, MODBUSCMD) 

        self.add_control("start_engine", cmdreg, 0x01FE, 0x0000, 1)
        self.add_control("stop_engine", cmdreg, 0x02FD, 0x0000, 1)
        self.add_control("open_gcb", cmdreg, 0x11F0, 0x0000, 2)
        self.add_control("close_gcb", cmdreg, 0x11EF, 0x0000, 2)
        self.add_control("fault_reset", cmdreg, 0x08F7, 0x0000, 1)
        self.add_control("fault_reset_ecu", cmdreg, 0x10EF, 0x0000, 1)

        self.add_control("open_f1cb", self.set_feeder_breaker, "F1", False)
        self.add_control("open_f2cb", self.set_feeder_breaker, "F2", False)
        self.add_control("open_f3cb", self.set_feeder_breaker, "F3", False)
        self.add_control("close_f1cb", self.set_feeder_breaker, "F1", True)
        self.add_control("close_f2cb", self.set_feeder_breaker, "F2", True)
        self.add_control("close_f3cb", self.set_feeder_breaker, "F3", True)

        self.add_control("system_start", self.sw1_set_bit, 14)
        self.add_control("system_stop", self.sw1_clear_bit, 14)
        self.add_control("emergency_stop", self.sw1_set_bit, 15)

    async def access(self, client):
        """Write access code"""

        addr = 46339 - 40001

        rr = await client.write_register(addr, self.access_code, slave=1)

        if rr.isError():
            raise IOError(f"Writing access code: {rr}")

    async def authenticate(self, client):
        """Write authentication code"""

        addr = 46363 - 40001

        data = [self.user_code, self.pass_code]

        rr = await client.write_registers(addr, data, slave=1)

        if rr.isError():
            raise IOError(f"Writing access code: {rr}")

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
            value = decoder.decode_string(reg.words * 2).decode("utf-8").rstrip("\x00")
        elif reg.type.startswith("Timer"):
            value = decoder.decode_64bit_int()
        elif reg.type.startswith("Char"):
            value = decoder.decode_string(1).decode("utf-8")[0].rstrip("\x00")
        elif reg.type == 'Date':
            value = decoder.decode_32bit_uint()
            #b = bcd_decode(decoder.decode_32bit_uint().to_bytes(4))
            #value = datetime.date(2000+b[2], b[1], b[0])
        elif reg.type == 'Time':
            value = decoder.decode_32bit_uint()
            #b = bcd_decode(decoder.decode_32bit_uint().to_bytes(4))
            #value = datetime.time(b[0], b[1], b[2])
        else:
            raise ValueError(f"Unknown type: {reg.type}")

        return value

    async def get_feeder_breaker(self, feeder_name):
        """Get feeder breaker state"""

        register = feeder_breaker_state[feeder_name] 
        value = await self.read_register_path(register.path)
        state = bitlib.get_bit(value, register.bit) 

        return state

    async def set_feeder_breaker(self, feeder_name, state):

        if self.get_feeder_breaker(feeder_name) == state:
            return True

        bit = { "F1": 0, "F2": 5, "F3": 7 }[feeder_name]

        return await self.sw1_pulse_bit(bit)

    async def sw1_pulse_bit(self, bit_index, pulse_width=0.2):

        value = await self.read_register_path("/Log_Bout/ModbusSw1")

        await self.write_register_addr(MODBUSSW1, clear_bit(value, bit_index))
        await asyncio.sleep(pulse_width)

        await self.write_register_addr(MODBUSSW1, set_bit(value, bit_index))
        await asyncio.sleep(pulse_width)

        await self.write_register_addr(MODBUSSW1, clear_bit(value, bit_index))
        await asyncio.sleep(pulse_width)

        return True

    async def sw1_set_bit(self, *args, **kwargs): 
        """Set sw1 bits""" 

        curvalue = await self.read_register_path("/Log_Bout/ModbusSw1")
        newvalue = set_bit(curvalue, *args, **kwargs) 

        return await self.write_register_addr(MODBUSSW1, newvalue) 

    async def sw1_clear_bit(self, *args, **kwargs): 

        curvalue = await self.read_register_path("/Log_Bout/ModbusSw1")
        newvalue = clear_bit(curvalue, *args, **kwargs)

        return await self.write_register_addr(MODBUSSW1, newvalue) 

    async def set_controller_mode(self, mode):
        addr = 43027 - 40001
        return await self.write_register_addr(addr, mode)


class SGM(GensetMeter):

    def __init__(self, *args, **kwargs):
        GensetMeter.__init__(self, *args, **kwargs)

        self.add_control("loadbank_up", self.sw1_pulse_bit, 1)
        self.add_control("loadbank_down", self.sw1_pulse_bit, 2)
        self.add_control("loadbank_reset", self.sw1_pulse_bit, 3)
        self.add_control("loadbank_mode_auto", self.sw1_clear_bit, 4)
        self.add_control("loadbank_mode_remote", self.sw1_set_bit, 4)
        self.add_control("loadbank_override", self.sw1_set_bit, 6)
        self.add_control("loadbank_clear_override", self.sw1_clear_bit, 6)
        self.add_control("loadbank_status", self.loadbank_status) 

        self.add_control("espar_heater_off", self.sw1_pulse_bit, 11)
        self.add_control("espar_heater_on", self.sw1_pulse_bit, 12)
        self.add_control("fuel_fill_trigger", self.sw1_pulse_bit, 13)

        setpwr = partial(self.sw1_set_bit, 9, mask=0b11)

        self.add_control("min_run_power0", setpwr, num=0)
        self.add_control("min_run_power1", setpwr, num=1)
        self.add_control("min_run_power2", setpwr, num=2)

        self.add_control("mode_off", self.set_controller_mode, 0)
        self.add_control("mode_man", self.set_controller_mode, 1)
        self.add_control("mode_auto", self.set_controller_mode, 3)

    async def loadbank_status(self):
        """Return loadbank settings"""

        """
        returns current load setting, mode, and override
        load setting is in kW, mode is 0 for auto and 1
        for remote, and override active is 1
        
        can get current load status from these bits:
             LB1STEP10KW - BOUT - bit 12
             LB2STEP20KW - BOUT - bit 13
             LB3STEP20KW - BOUT - bit 14
             LB4STEP50KW - BOUT - bit 15
             LB5STEP50KW - BOUT-1 - bit 5
        and we can get the mode by reading MODBUSSW
        mode is bit 4 and override is bit 6
        """

        bout = await self.read_register_path("/Bin_outputs_CU/BOUT")
        bout1 = await self.read_register_path("/Binary_Outputs/BOUT-1")
        sw1 = await self.read_register_path("/Log_Bout/ModbusSw1")

        return self.parse_loadbank_status(bout, bout1, sw1)

    def parse_loadbank_status(self, bout, bout1, sw1):

        lb_1_step_10KW = get_normalized_bit(bout, 12)
        lb_2_step_20KW = get_normalized_bit(bout, 13)
        lb_3_step_20KW = get_normalized_bit(bout, 14)
        lb_4_step_50KW = get_normalized_bit(bout, 15)
        lb_5_step_50KW = get_normalized_bit(bout1, 5)

        load_bank_bits = [
            lb_1_step_10KW,
            lb_2_step_20KW,
            lb_3_step_20KW,
            lb_4_step_50KW,
            lb_5_step_50KW,
        ]

        setting = sum([
            lb_1_step_10KW * 10,
            lb_2_step_20KW * 20,
            lb_3_step_20KW * 20,
            lb_4_step_50KW * 50,
            lb_5_step_50KW * 50,
        ])

        mode = get_normalized_bit(sw1, 4)
        override = get_normalized_bit(sw1, 6)

        return {
            "setting": setting, 
            "mode": mode, 
            "override": override, 
            "bits": load_bank_bits
        }

    async def read_virtual(self, state):
        return {
            "/Virtual/loadbank_status":  self.virtual_loadbank_status(state)
        }

    def virtual_loadbank_status(self, state):
        bout = state["/Bin_outputs_CU/BOUT"]["value"]
        bout1 = state["/Binary_Outputs/BOUT-1"]["value"]
        sw1 = state["/Log_Bout/ModbusSw1"]["value"]

        return { "value": self.parse_loadbank_status(bout, bout1, sw1) }


class MGM(GensetMeter):

    def __init__(self, *args, **kwargs):
        GensetMeter.__init__(self, *args, **kwargs)

        self.add_control("mode_off", self.set_controller_mode, 0)
        self.add_control("mode_man", self.set_controller_mode, 1)
        self.add_control("mode_auto", self.set_controller_mode, 2)


