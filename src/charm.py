#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""MySQL-Router machine charm."""

import json
import logging
import subprocess
from typing import Optional

from charms.operator_libs_linux.v1 import snap
from ops.charm import CharmBase, RelationChangedEvent
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, WaitingStatus

from constants import (
    CHARMED_MYSQL_ROUTER_SERVICE,
    CHARMED_MYSQL_SNAP,
    LEGACY_SHARED_DB,
    MYSQL_ROUTER_LEADER_BOOTSTRAPED,
    MYSQL_ROUTER_REQUIRES_DATA,
    PEER,
)
from mysql_router_helpers import (
    MySQLRouter,
    MySQLRouterBootstrapError,
    MySQLRouterInstallCharmedMySQLError,
)
from relations.database_provides import DatabaseProvidesRelation
from relations.database_requires import DatabaseRequiresRelation
from relations.shared_db import SharedDBRelation

logger = logging.getLogger(__name__)


class MySQLRouterOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on[PEER].relation_changed, self._on_peer_relation_changed)

        self.shared_db_relation = SharedDBRelation(self)
        self.database_requires_relation = DatabaseRequiresRelation(self)
        self.database_provides_relation = DatabaseProvidesRelation(self)

    # =======================
    # Properties
    # =======================

    @property
    def _peers(self):
        """Retrieve the peer relation."""
        return self.model.get_relation(PEER)

    @property
    def app_peer_data(self):
        """Application peer data object."""
        if not self._peers:
            return {}

        return self._peers.data[self.app]

    @property
    def unit_peer_data(self):
        """Unit peer data object."""
        if not self._peers:
            return {}

        return self._peers.data[self.unit]

    # =======================
    #  Helpers
    # =======================

    def _get_secret(self, scope: str, key: str) -> Optional[str]:
        """Get secret from the peer relation databag."""
        if scope == "unit":
            return self.unit_peer_data.get(key, None)
        elif scope == "app":
            return self.app_peer_data.get(key, None)
        else:
            raise RuntimeError("Unknown secret scope.")

    def _set_secret(self, scope: str, key: str, value: Optional[str]) -> None:
        """Set secret in the peer relation databag."""
        if scope == "unit":
            if not value:
                del self.unit_peer_data[key]
                return
            self.unit_peer_data.update({key: value})
        elif scope == "app":
            if not value:
                del self.app_peer_data[key]
                return
            self.app_peer_data.update({key: value})
        else:
            raise RuntimeError("Unknown secret scope.")

    # =======================
    #  Handlers
    # =======================

    def _on_install(self, _) -> None:
        """Install the mysql-router package."""
        self.unit.status = MaintenanceStatus("Installing packages")

        try:
            MySQLRouter.install_charmed_mysql()
        except MySQLRouterInstallCharmedMySQLError:
            self.unit.status = BlockedStatus("Failed to install mysqlrouter")
            return

        for port in [6446, 6447, 6448, 6449]:
            try:
                subprocess.check_call(["open-port", f"{port}/tcp"])
            except subprocess.CalledProcessError:
                logger.exception(f"failed to open port {port}")

        self.unit.status = WaitingStatus("Waiting for relations")

    def _on_upgrade_charm(self, _) -> None:
        """Update the mysql-router config on charm upgrade."""
        if isinstance(self.unit.status, ActiveStatus):
            self.unit.status = MaintenanceStatus("Upgrading charm")

            requires_data = json.loads(self.app_peer_data.get(MYSQL_ROUTER_REQUIRES_DATA))

            try:
                MySQLRouter.bootstrap_and_start_mysql_router(
                    requires_data["username"],
                    self._get_secret("app", "database-password"),
                    requires_data["endpoints"].split(",")[0].split(":")[0],
                    "3306",
                    force=True,
                )
            except MySQLRouterBootstrapError:
                self.unit.status = BlockedStatus("Failed to bootstrap mysqlrouter")
                return

            self.unit.status = ActiveStatus()

    def _on_peer_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle the peer relation changed event.

        If a peer is being joined for the first time, bootstrap mysqlrouter
        and share relevant connection data with the related app.
        """
        if isinstance(self.unit.status, WaitingStatus) and self.app_peer_data.get(
            MYSQL_ROUTER_LEADER_BOOTSTRAPED
        ):
            try:
                cache = snap.SnapCache()
                charmed_mysql = cache[CHARMED_MYSQL_SNAP]

                mysqlrouter_running = charmed_mysql.services[CHARMED_MYSQL_ROUTER_SERVICE][
                    "active"
                ]
            except snap.SnapError:
                logger.exception("Failed to check if mysqlrouter service is running")
                self.unit.status = BlockedStatus("Failed to bootstrap mysqlrouter")
                return

            if not self.unit.is_leader() and not mysqlrouter_running:
                # Occasionally, the related unit is not in the relation databag if this handler
                # is invoked in short succession after the peer joins the cluster
                shared_db_relation_exists = self.shared_db_relation._shared_db_relation_exists()
                shared_db_related_unit_name = self.shared_db_relation._get_related_unit_name()
                if shared_db_relation_exists and not shared_db_related_unit_name:
                    event.defer()
                    return

                requires_data = json.loads(self.app_peer_data.get(MYSQL_ROUTER_REQUIRES_DATA))

                try:
                    MySQLRouter.bootstrap_and_start_mysql_router(
                        requires_data["username"],
                        self._get_secret("app", "database-password"),
                        requires_data["endpoints"].split(",")[0].split(":")[0],
                        "3306",
                    )
                except MySQLRouterBootstrapError:
                    self.unit.status = BlockedStatus("Failed to bootstrap mysqlrouter")
                    return

                if shared_db_relation_exists:
                    self.model.relations[LEGACY_SHARED_DB][0].data[self.unit].update(
                        {
                            "allowed_units": shared_db_related_unit_name,
                            "db_host": "127.0.0.1",
                            "db_port": "3306",
                            "password": self._get_secret("app", "application-password"),
                            "wait_timeout": "3600",
                        }
                    )

            self.unit.status = ActiveStatus()


if __name__ == "__main__":
    main(MySQLRouterOperatorCharm)
