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

import datetime
import json 

def json_serial(obj):
    """JSON serializer for objects"""

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()

    elif isinstance(obj, datetime.timedelta):
        return obj.total_seconds()

    raise TypeError(f"Type {type(obj)} not serializable")

def output(obj):
    """Serialize obj if not None"""

    if obj is None:
        return None

    return json.dumps(obj, default=json_serial).encode("utf-8")

