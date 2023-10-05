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
#   2023-09-25  Todd Valentic
#               Use meter_regmap base class
#
##########################################################################

import argparse
import json
import sys

from meter_regmap import Register, RegisterMap, test


class AcuvimIIRegister(Register):
    """Individual register"""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-few-public-methods

    def parse(self, entry):
        """Parse fields"""

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

class AcuvimIIRegisters(RegisterMap):
    """Register Map"""

    def load(self, filename):
        """Load mapping from definition file"""

        with open(filename, encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)

        for group_name, registers in data.items():
            for parameter, register in registers.items():
                register_name = parameter.lower().replace(" ", "_")
                register["group"] = group_name
                register["name"] = register_name
                register["path"] = f"/{group_name}/{register_name}"
                self.groups.add(AcuvimIIRegister(register))

def main():
    """Test application"""

    return test(AcuvimIIRegisters)

if __name__ == "__main__":
    sys.exit(main())
