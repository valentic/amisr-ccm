#!/usr/bin/env python3
"""Meter Register Map Base Class"""

##########################################################################
#
#   Meter register map base class
#
#
#   2023-09-25  Todd Valentic
#               Initial implementation.
#               Extracted from individual meter regmaps
#
##########################################################################

from abc import ABC, abstractmethod
import argparse


class Register(ABC):
    """Individual register"""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-few-public-methods

    def __init__(self, entry):
        ABC.__init__(self)

        self.group = None
        self.name = None
        self.value = None
        self.scale = None
        self.raw_value = None
        self.address = None
        self.description = None
        self.words = None
        self.type = None
        self.unit = None

        self.parse(entry)

    @abstractmethod
    def parse(self, line):
        """Parse fields from text line"""

    def set(self, value):
        """Store current reading"""

        self.raw_value = value

        if self.scale:
            value = value / self.scale

        self.value = value

    def details(self):
        """Register details"""

        return {
            "description": self.description,
            "unit": self.unit,
            "scale": self.scale,
            "type": self.type,
            "words": self.words,
        }


class Group:
    """Logical group of registers"""

    def __init__(self, name):
        self.name = name
        self.registers = []
        # self.max_block_words = 64
        self.max_block_words = 125

    def add(self, register):
        """Add a register to the group"""
        self.registers.append(register)

    def list_registers(self):
        """List register paths in group"""
        return [reg.path for reg in self.registers]

    def list_register_details(self):
        """List details for registers"""
        return {reg.path: reg.details() for reg in self.registers}

    def get_blocks(self):
        """Return blocks of registers with contiguous address"""

        if not self.registers:
            return []

        sorted_regs = sorted(self.registers, key=lambda x: x.address)

        blocks = []
        curblock = [sorted_regs[0]]
        numwords = sorted_regs[0].words

        for reg in sorted_regs[1:]:
            curreg = curblock[-1]
            next_addr = curreg.address + curreg.words
            if next_addr == reg.address and numwords < self.max_block_words:
                curblock.append(reg)
                numwords += reg.words
            else:
                blocks.append(curblock)
                curblock = [reg]
                numwords = reg.words

        blocks.append(curblock)

        return blocks

    def get_block(self, path):
        """Return a block holding the register at path"""

        if not self.registers:
            return []

        try:
            register = next(reg for reg in self.registers if reg.path == path)
        except StopIteration as exc:
            raise RuntimeError(f"Unknown register {path}") from exc

        return [register]


class Groups:
    """Register Groups"""

    def __init__(self):
        self.groups = {}

    def add(self, register):
        """Add register to group"""

        name = register.group
        if name not in self.groups:
            self.groups[name] = Group(name)

        self.groups[name].add(register)

    def get_blocks(self, group_name, register_path=None):
        """Get register blocks for a group"""

        if register_path:
            return self.groups[group_name].get_block(register_path)

        return self.groups[group_name].get_blocks()

    def list_groups(self):
        """List group names"""

        return list(self.groups)

    def list_registers(self):
        """List register paths"""

        results = {}

        for group in self.groups.values():
            results[group.name] = group.list_registers()

        return results

    def list_register_details(self):
        """Return register details"""

        results = {}

        for group in self.groups.values():
            results.update(group.list_register_details())

        return results


class RegisterMap(ABC):
    """Register Map"""

    def __init__(self, filename):
        ABC.__init__(self)

        self.groups = Groups()
        self.load(filename)

    @abstractmethod
    def load(self, filename):
        """Load mapping from definition file"""

    def list_groups(self):
        """List group names"""

        return self.groups.list_groups()

    def list_registers(self):
        """List registers in each group"""

        return self.groups.list_registers()

    def list_register_details(self):
        """List register details"""

        return self.groups.list_register_details()

    def get_register_blocks(self, group_name):
        """Return the register block list for a group"""

        return self.groups.get_blocks(group_name)

    def get_register_block(self, path):
        """Return the register block list for a single register"""

        group_name = path.split("/")[1]
        return self.groups.get_blocks(group_name, register_path=path)

    def get_register(self, path):
        """Return the register at path"""

        return self.get_register_block(path)[0]


def test(registermap):
    """Test application"""

    desc = "Load register fields"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("filename")

    args = parser.parse_args()

    regmap = registermap(args.filename)

    for group in regmap.list_groups():
        print(f"----- {group} ----")
        for block in regmap.get_register_blocks(group):
            for reg in block:
                print(
                    f"{reg.address} {reg.words} {reg.type} {reg.description} {reg.path}"
                )

    return 0
