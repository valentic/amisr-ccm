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


def get_bit(value, index, **kwargs):
    """Get bits"""

    mask = kwargs.get("mask", 1)
    return value & (mask << index)


def get_normalized_bit(value, index, **kwargs):
    """Get bits, normalized"""

    mask = kwargs.get("mask", 1)
    return (value >> index) & mask


def set_bit(value, index, **kwargs):
    """Set bits"""

    mask = kwargs.get("mask", 1)
    num = kwargs.get("num", 1)
    value = clear_bit(value, index, mask=mask)
    return value | (num << index)


def clear_bit(value, index, **kwargs):
    """Clear bits"""

    mask = kwargs.get("mask", 1)
    return value & ~(mask << index)


def toggle_bit(value, index, **kwargs):
    """Toggle bits"""

    mask = kwargs.get("mask", 1)
    return value ^ (mask << index)


def bcd_decode(data: bytes):
    """Decode BCD value"""

    result = []

    for b in data:
        result.append((b >> 4) * 10 + (b & 0x0F))

    return result
