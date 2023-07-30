#!/usr/bin/env python3
"""Monitor tincan network configuration"""

##################################################################
#
#   Monitor for tincan network config changes
#
#   Post latest version of the tincan configuration file to the
#   cache service.
#
#   2021-06-30  Todd Valentic
#               Initial implementation.
#
#   2023-07-07  Todd Valentic
#               Updated for transport3 / python3
#
##################################################################

import hashlib
import json

from datamonitor import DataMonitorComponent

class TincanMonitor(DataMonitorComponent):
    """Tincan network data monitor"""

    def __init__(self, *pos, **kw):
        DataMonitorComponent.__init__(self, *pos, **kw)

        self.config_filename = self.config.get_path(
            "tincan.configfile", "/etc/tincan/data/config.json"
        )

        self.checksum = None
        self.cache_key = "tincan"

    def load_tincan_config(self, path):
        """Load tincan configuration data"""

        payload = path.read_text('utf-8')
        data = json.loads(payload)
        checksum = hashlib.md5(payload.encode('utf-8')).hexdigest()

        return data, checksum

    def sample(self):
        """Check tincan configuration"""

        if not self.config_filename.exists():
            self.log.debug("No config file found: %s", self.config_filename)
            return None

        try:
            data, checksum = self.load_tincan_config(self.config_filename)
        except: # pylint: disable=bare-except
            self.log.exception("Problem parsing the config file")
            return None

        if self.cache_key not in self.list_cache():
            self.checksum = None

        if checksum != self.checksum:
            self.log.info("Detected modified config")
            self.put_cache(self.cache_key, data)
            self.checksum = checksum

        if self.cache_key not in self.list_cache():
            self.put_cache(self.cache_key, data)

        return None
