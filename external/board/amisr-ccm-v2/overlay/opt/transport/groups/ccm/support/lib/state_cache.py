#!/usr/bin/env python
"""Local state cache"""

##########################################################################
#
#   Local state cache
#
#   2023-10-11  Todd Valentic
#               Initial implementation
#
##########################################################################

import time


class StateCache:
    """Data Cache"""

    def __init__(self, max_age=15):
        self.data = None
        self.time = 0
        self.max_age = max_age

    def is_valid(self, max_age=None):
        """Return true if cache data is new enough"""

        if max_age is None:
            max_age = self.max_age

        if self.data:
            age = time.monotonic() - self.time
            return age < max_age

        return False

    def empty(self):
        """Return true if no data has been set"""
        return self.data is None

    def get(self):
        """Return cached data"""
        return self.data

    def put(self, data):
        """Set cached data"""
        self.data = data
        self.time = time.monotonic()

    def update(self, data):
        """Update cached data, keep timestamp"""
        self.data = data

    def clear(self):
        """Clear current data"""
        self.data = None
        self.time = 0

    def mark_dirty(self):
        """Mark data as dirty"""
        self.time = 0
