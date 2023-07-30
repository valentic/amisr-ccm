#!/usr/bin/env python3
"""SBD Message Type Catalog"""

##########################################################################
#
#   CCM SBD Types
#
#   2023-07-11  Todd Valentic
#               Initial implementation
#
##########################################################################

from enum import Enum

class MessageType(Enum):
    """SBD Message Types"""

    CCM_COMMAND = 0
    SHELL_COMMAND = 1
    FILE_UPLOAD = 2


class FileFlags(Enum):
    """File upload flags"""

    EXECUTE = 0x01
    COMPRESSED = 0x02
    REMOVE = 0x04
