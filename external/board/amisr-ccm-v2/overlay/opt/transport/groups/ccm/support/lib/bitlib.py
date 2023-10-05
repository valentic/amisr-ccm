#!/usr/bin/env python3
"""Bit manipulation library"""

##########################################################################
#
#   Bit manipulation library
#
#   2023-10-02  Todd Valentic
#               Initial implementation
#
##########################################################################

def get_bit(value, index, mask=1):
    return value & (mask << index)

def get_normalized_bit(value, index, mask=1):
    return (value >> index) & mask 

def set_bit(value, index, mask=1, num=1):
    value = clear_bit(value, index, mask)
    return value | (num << index)

def clear_bit(value, index, mask=1):
    return value & ~(mask << index)

def toggle_bit(value, index, mask=1):
    return value ^ (mask << index)

def bcd_decode(data: bytes):

    result = []

    for b in data: 
        result.append((b >> 4) * 10 + (b & 0x0F))

    return result

