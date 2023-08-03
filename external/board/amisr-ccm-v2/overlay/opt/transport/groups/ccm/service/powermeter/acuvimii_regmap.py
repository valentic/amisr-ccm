#!/usr/bin/env python3
"""Acuvim II Register Map"""

##########################################################################
#
#   Create register map file from vender file (which extracted from the
#   PDF manual).
#
#   Acuvim-II-Power-Meter-User-Manual-1040E1303.pdf
#
#   2023-08-02  Todd Valentic
#               Initial implementation. Based on code from John Jorgensen
#
##########################################################################

import argparse
import json
import sys


class Register:
    """Individual register"""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-few-public-methods

    def __init__(self, entry):
        self.group = entry["group"]
        self.description = entry["Parameters"]
        self.type = entry["Data Type"].lower()
        self.path = entry["path"]
        self.value = None
        self.raw_value = None
        self.scale = None

        if "Unit" in entry:
            self.unit = entry["Unit"]
        else:
            self.unit = ""

        addr = entry["Address"].lower().replace("h", "").split("~")
        addr = [int(x, base=16) for x in addr]
        if len(addr) == 2:
            self.words = addr[1] - addr[0] + 1
            self.address = addr[0]
        else:
            self.words = 1
            self.address = addr[0]

    def set(self, value):
        """Store current reading"""

        self.raw_value = value

        if self.scale:
            value = value / self.scale

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


class AcuvimIIRegisters:
    """Register Map"""

    def __init__(self, filename):
        self.registers = self.load(filename)

        self.groups = self.load(filename)

    def load(self, filename):
        """Load mapping from definition file"""

        groups = Groups()

        with open(filename, encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)

        for group_name, registers in data.items():
            for parameter, register in registers.items():
                register_name = parameter.lower().replace(" ", "_")
                register["group"] = group_name
                register["name"] = register_name
                register["path"] = f"/{group_name}/{register_name}"
                groups.add(Register(register))

        return groups

    def list_groups(self):
        """List group names"""

        return self.groups.list_groups()

    def get_register_blocks(self, group_name):
        """Return the register block list for a group"""

        return self.groups.get_blocks(group_name)


def main():
    """Test application"""

    desc = "Load Acuvim-II register fields"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("filename")

    args = parser.parse_args()

    regmap = AcuvimIIRegisters(args.filename)

    print("Registers in system group:")

    for group in regmap.list_groups():
        print(f"----- {group} ----")
        for block in regmap.get_register_blocks(group):
            for reg in block:
                print(f"{reg.address} {reg.words} {reg.type} {reg.description}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
