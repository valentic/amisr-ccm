#!/usr/bin/env python

##########################################################################
#
#   Parse register type fields (Binary, List)
#
#   2023-10-11  Todd Valentic
#               Initial implementation
#
##########################################################################

import re
from enum import Enum, auto

class State(Enum):
    FIND_START = auto(),
    FIND_TYPE_LINE = auto(),
    READ_ENTRY = auto(),

def is_dashed_line(line):
        chars = set(line)
        return len(chars) == 1 and len(line)>1 and '-' in chars

def parse_types(contents):

    results = {}

    line_num = 0
    state = State.FIND_START
    name = None

    while line_num < len(contents):
        line = contents[line_num]
        line_num += 1 

        if state == State.FIND_START:
            if is_dashed_line(line):
                state = State.FIND_TYPE_LINE

        elif state == State.FIND_TYPE_LINE:
            if line.startswith("Binary#") or line.startswith("List#"):
                name = line
                results[name] = {} 
                state = State.READ_ENTRY
                line_num += 3 
            else:
                state = State.FIND_START

        elif state == State.READ_ENTRY:
            index_label = r"\s*(\d+)\s*(.+\S).*"

            match = re.match(index_label, line)

            if match:
                index, label = match[1], match[2]
                results[name][index] = label
            else:
                state = State.FIND_START

    return results

if __name__ == "__main__":

    import sys
    from pprint import pprint

    filename = sys.argv[1]

    with open(filename, "r", encoding="iso-8859-1") as datafile:
        contents = datafile.read().split("\n")

    results = parse_types(contents)

    pprint(results)
