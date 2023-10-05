#!/usr/bin/env python3
"""ComAp Register Map"""

##########################################################################
#
#   Create register map file from vender supplied file
#
#
#   2023-08-03  Todd Valentic
#               Initial implementation.
#               Based on code from John Jorgensen and Ashton Reimer
#
#   2023-08-24  Todd Valentic
#               Use ISO-8859-1 enocding for register map files.
#
#   2023-09-25  Todd Valentic
#               Use meter_Regmap base class
#               Convert "/" in group name to be "_"
#
##########################################################################

import math
import sys

from pathlib import Path

from meter_regmap import Register, RegisterMap, test


def conv_empty(value):
    """Map - to empty string"""
    return "" if value == "-" else value


def conv_int(value):
    """Convert to int unless -"""
    return None if value == "-" else int(value)


def conv_nospace(value):
    """Convert spaces and / to underlines"""
    return value.replace(" ", "_").replace("/","_")

def conv_words(value):
    num_bytes = int(value)
    return math.ceil(num_bytes / 2)

class GensetRegister(Register):
    """Individual register"""

    # pylint: disable=too-few-public-methods

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
            self.scale = math.pow(10, self.decimals)

        self.path = f"/{self.group}/{self.name}"
        self.address = self.register - 40000 - 1
        self.description = self.name.replace("_", " ")

class SpecialRegister(Register):
    """Control register not listed in map file"""

    def __init__(self, **kwargs): 
        Register.__init__(self, kwargs)

    def parse(self, entry):
        self.group = entry.get("group", "Special")
        self.name = entry["name"]
        self.register = entry["register"]
        self.type = entry.get("datatype", "Binary")
        self.words = entry.get("words", 1) 
        self.unit = entry.get("unit", None)

        self.path = f"/{self.group}/{self.name}"
        self.address = self.register - 40001
        self.description = self.name.replace("_", " ")


class GensetRegisters(RegisterMap):
    """Register Map"""

    def load(self, filename):
        """Load mapping from definition file"""

        contents = Path(filename).read_text("iso-8859-1").split("\n")

        # register section starts at line 3 until blank line

        registers = []

        for line in contents[2:]:
            if not line:
                break
            registers.append(GensetRegister(line))

        self.resolve_minmax(registers)

        for register in registers:
            self.groups.add(register)

        self.add_alarms()

    def add_alarms(self):
        """Add alarm group registers"""

        ALARM_START_REG = 46669
        ALARM_NUM_WORDS = 25

        for k in range(16):
            self.groups.add(SpecialRegister(
                group = "Alarms",
                name = f"Alarm_{k:02}",
                register = ALARM_START_REG + (k*ALARM_NUM_WORDS),
                datatype = "String0",
                words =  ALARM_NUM_WORDS
            ))

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

def main():
    """Test application"""

    return test(GensetRegisters)

if __name__ == "__main__":
    sys.exit(main())
