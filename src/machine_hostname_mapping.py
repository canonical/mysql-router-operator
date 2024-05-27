# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""hostname mapping configuration"""

import logging

from python_hosts import Hosts, HostsEntry

from relations.database_requires import CompleteConnectionInformation

logger = logging.getLogger(__name__)

COMMENT = "Managed by mysql-router charm"


class MachineHostnameMapping:
    """Machine hostname mapping configuration"""

    def __init__(self) -> None:
        self._hosts = Hosts()

    def update_etc_hosts(self, connection_info: CompleteConnectionInformation) -> None:
        """Add a host to the hosts file.

        Args:
            connection_info: The relation CompleteConnectionInformation
        """
        if connection_info.hostname_mapping is None:
            logger.debug("No hostname mapping to update")
            return

        logger.debug("Updating /etc/hosts")
        host_entries = [
            HostsEntry(entry_type="ipv4", comment=COMMENT, **entry)
            for entry in connection_info.hostname_mapping
        ]

        self._hosts.remove_all_matching(comment=COMMENT)
        self._hosts.add(host_entries, force=True, allow_address_duplication=True, merge_names=True)
        self._hosts.write()
