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
#   2023-09-25  Todd Valentic
#               Use meter_regmap base class
#
##########################################################################

import csv
import sys

from meter_regmap import Register, RegisterMap, test

class VictronRegister(Register):
    """Individual register"""

    def parse(self, entry):
        """Parse fields"""

        self.group = entry["dbus-service-name"].replace("com.victronenergy.", "")
        self.description = entry["description"]
        self.address = int(entry["Address"])
        self.type = entry["Type"]
        self.name = entry["dbus-obj-path"]
        self.path = f"/{self.group}{self.name}"
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

class VictronRegisters(RegisterMap):
    """Register Map"""

    def load(self, filename):
        """Load mapping from definition file"""

        with open(filename, encoding="utf-8") as csvfile:
            next(csvfile)  # Skip first line
            reader = csv.DictReader(csvfile)

            for row in reader:
                register = VictronRegister(row)
                self.groups.add(register)

def main():
    """Test application"""

    return test(VictronRegisters)


if __name__ == "__main__":
    sys.exit(main())
