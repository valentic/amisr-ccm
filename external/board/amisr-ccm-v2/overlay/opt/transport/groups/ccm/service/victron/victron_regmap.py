#!/usr/bin/env python3
"""Victron Register Map"""

##########################################################################
#
#   Create register map file from vender CSV file
#
#   CCGX-Modbus-TCP-register-list-3.00
#
#   Saved Field list table (first page) out
#
#   2023-08-01  Todd Valentic
#               Initial implementation
#
##########################################################################

import argparse
import csv
import sys


class Register:
    """Individual register"""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, entry):
        self.group = entry["dbus-service-name"].replace("com.victronenergy.", "")
        self.description = entry["description"]
        self.address = int(entry["Address"])
        self.type = entry["Type"]
        self.path = entry["dbus-obj-path"]
        self.unit = entry["dbus-unit"]
        self.value = None
        self.raw_value = None

        if self.type.startswith("string"):
            self.words = int(self.type.split("[")[1].split("]")[0])
        elif self.type.endswith("16"):
            self.words = 1
        elif self.type.endswith("32"):
            self.words = 2
        else:
            raise ValueError(f"Unknown type: {self.type}")

        if self.type.startswith("string"):
            self.scale = None
        else:
            self.scale = float(entry["Scalefactor"])

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

    def add(self, register):
        """Add a register to the group"""
        self.registers.append(register)
        self.registers.sort(key=lambda x: x.address)

    def get_blocks(self):
        """Return blocks of registers with contiguous address"""

        if not self.registers:
            return []

        sorted_regs = sorted(self.registers, key=lambda x: x.address)

        blocks = []
        curblock = [sorted_regs[0]]

        for reg in sorted_regs[1:]:
            curreg = curblock[-1]
            next_addr = curreg.address + curreg.words
            if next_addr == reg.address:
                curblock.append(reg)
            else:
                blocks.append(curblock)
                curblock = [reg]

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


class VictronRegisters:
    """Register Map"""

    def __init__(self, filename):
        self.groups = self.load(filename)

    def load(self, filename):
        """Load mapping from definition file"""

        groups = Groups()

        with open(filename, encoding="utf-8") as csvfile:
            next(csvfile)  # Skip first line
            reader = csv.DictReader(csvfile)

            for row in reader:
                register = Register(row)
                groups.add(register)

        return groups

    def get_register_blocks(self, group_name):
        """Return the register block list for a group"""

        return self.groups.get_blocks(group_name)


def main():
    """Test application"""

    desc = "Load victron register fields"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("filename")

    args = parser.parse_args()

    regmap = VictronRegisters(args.filename)

    print("Registers in system group:")

    for block in regmap.get_register_blocks("system"):
        print("-----")
        for reg in block:
            print(f"{reg.address} {reg.description}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
