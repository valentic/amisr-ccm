#!/usr/bin/env python3
"""Acuvim II Register Map"""

##########################################################################
#
#   Create register map file from vender supplied file
#
#
#   2023-08-03  Todd Valentic
#               Initial implementation.
#               Based on code from John Jorgensen and Ashton Reimer
#
##########################################################################

import argparse
import math
import sys

from pathlib import Path


def conv_empty(value):
    """Map - to empty string"""
    return "" if value == "-" else value


def conv_int(value):
    """Convert to int unless -"""
    return None if value == "-" else int(value)


def conv_nospace(value):
    """Convert spaces to underlines"""
    return value.replace(" ", "_")

def conv_words(value):
    num_bytes = int(value)
    return math.ceil(num_bytes / 2)

class Register:
    """Individual register"""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-few-public-methods

    def __init__(self, line):

        self.group = None
        self.name = None
        self.value = None
        self.scale = None
        self.raw_value = None

        self.parse(line)

    def parse(self, line):
        """Parse fields from text line"""

        # Remove unwanted chars
        line = line.replace("\xb0", " ")  # degree symbol

        fields = {
            "register": (0, 5, int),
            "comm_obj": (17, 26, int),
            "name": (26, 41, conv_nospace),
            "unit": (41, 46, conv_empty),
            "type": (46, 57, str),
            "words": (57, 61, conv_words),
            "decimals": (61, 64, conv_int),
            "min_val": (64, 71, conv_empty),
            "max_val": (71, 78, conv_empty),
            "group": (78, None, conv_nospace),
        }

        for field, (start, end, conv) in fields.items():
            value = conv(line[start:end].strip())
            setattr(self, field, value)

        if self.decimals is None:
            self.scale = None
        else:
            self.scale = math.pow(10, -self.decimals)

        self.path = f"/{self.group}/{self.name}"
        self.address = self.register - 40000 - 1
        self.description = self.name.replace("_", " ")

    def set(self, value):
        """Store current reading"""

        self.raw_value = value

        if self.scale:
            value = value * self.scale

        self.value = value


class Group:
    """Logical group of registers"""

    def __init__(self, name):
        self.name = name
        self.registers = []
        self.max_block_words = 64

    def add(self, register):
        """Add a register to the group"""
        self.registers.append(register)

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

    def get_blocks(self, name):
        """Get register blocks for a group"""

        return self.groups[name].get_blocks()

    def list_groups(self):
        """List group names"""

        return list(self.groups)


class GensetRegisters:
    """Register Map"""

    def __init__(self, filename):
        self.groups = self.load(filename)

    def load(self, filename):
        """Load mapping from definition file"""

        groups = Groups()

        contents = Path(filename).read_text("utf-8").split("\n")

        # register section starts at line 3 until blank line

        registers = []

        for line in contents[2:]:
            if not line:
                break
            registers.append(Register(line))

        self.resolve_minmax(registers)

        for register in registers:
            groups.add(register)

        return groups

    def resolve_minmax(self, registers):
        """Resolve min and max values"""

        comm_objs = {f"{reg.comm_obj}*": reg for reg in registers}

        for reg in registers:
            if reg.max_val:
                if reg.max_val.endswith("*"):
                    reg.max_val = comm_objs[reg.max_val].max_val
                reg.max_val = int(reg.max_val)
            else:
                reg.max_val = None

            if reg.min_val:
                if reg.min_val.endswith("*"):
                    reg.min_val = comm_objs[reg.min_val].min_val
                reg.min_val = int(reg.min_val)
            else:
                reg.min_val = None

    def list_groups(self):
        """List group names"""

        return self.groups.list_groups()

    def get_register_blocks(self, group_name):
        """Return the register block list for a group"""

        return self.groups.get_blocks(group_name)


def main():
    """Test application"""

    desc = "Load genset register fields"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("filename")

    args = parser.parse_args()

    regmap = GensetRegisters(args.filename)

    print("Registers in system group:")

    for group in regmap.list_groups():
        print(f"----- {group} ----")
        for block in regmap.get_register_blocks(group):
            for reg in block:
                print(f"{reg.address} {reg.words} {reg.type} {reg.description}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
