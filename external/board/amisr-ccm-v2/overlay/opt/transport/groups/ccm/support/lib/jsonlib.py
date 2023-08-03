#!/usr/bin/env python3
"""JSON serializer helper"""

##########################################################################
#
#   Serialize non-standard objects (i.e. datetime)
#
#   2027-08-02  Todd Valentic
#               Initial implementation
#
##########################################################################

import json 

from datetime import datetime, timedelta

def json_serial(obj):
    """JSON serializer for objects"""

    if isinstance(obj, datetime):
        return obj.isoformat()

    elif isinstance(obj, timedelta):
        return obj.total_seconds()

    raise TypeError(f"Type {type(obj)} not serializable")

def output(obj):
    return json.dumps(obj, default=json_serial).encode("utf-8")

