#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""MySQL-Router machine charm."""

import json
import logging
from typing import Optional

from charms.operator_libs_linux.v1 import systemd
from ops.charm import CharmBase, RelationChangedEvent
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, WaitingStatus

from constants import (
    LEGACY_SHARED_DB,
    MYSQL_ROUTER_BOOTSTRAPED,
    MYSQL_ROUTER_DATABASE_DATA,
    PEER,
)
from mysql_router_helpers import (
    MySQLRouter,
    MySQLRouterBootstrapError,
    MySQLRouterInstallAndConfigureError,
)
from relations.database import DatabaseRequiresRelation
from relations.shared_db import SharedDBRelation

logger = logging.getLogger(__name__)


class MySQLRouterOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on[PEER].relation_changed, self._on_peer_relation_changed)

        self.shared_db_relation = SharedDBRelation(self)
        self.database_requires_relation = DatabaseRequiresRelation(self)

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
            MySQLRouter.install_and_configure_mysql_router()
        except MySQLRouterInstallAndConfigureError:
            self.unit.status = BlockedStatus("Failed to install mysqlrouter")
            return

        self.unit.status = WaitingStatus("Waiting for relations")

    def _on_peer_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle the peer relation changed event.

        If a peer is being joined for the first time, bootstrap mysqlrouter
        and share relevant connection data with the related app.
        """
        if isinstance(self.unit.status, WaitingStatus) and self.app_peer_data.get(
            MYSQL_ROUTER_BOOTSTRAPED
        ):
            try:
                mysqlrouter_running = MySQLRouter.is_mysqlrouter_running()
            except systemd.SystemdError as e:
                logger.exception("Failed to check if mysqlrouter with systemd", exc_info=e)
                self.unit.status = BlockedStatus("Failed to bootstrap mysqlrouter")
                return

            if not self.unit.is_leader() and not mysqlrouter_running:
                # Occasionally, the related unit is not in the relation databag if this handler
                # is invoked in short succession after the peer joins the cluster
                shared_db_related_unit_name = self.shared_db_relation._get_related_unit_name()
                if not shared_db_related_unit_name:
                    event.defer()
                    return

                database_relation_data = json.loads(
                    self._peers.data[self.app].get(MYSQL_ROUTER_DATABASE_DATA)
                )

                try:
                    MySQLRouter.bootstrap_and_start_mysql_router(
                        database_relation_data["username"],
                        self._get_secret("app", "database_password"),
                        self.shared_db_relation._get_related_app_name(),
                        database_relation_data["endpoints"].split(",")[0].split(":")[0],
                        "3306",
                    )
                except MySQLRouterBootstrapError:
                    self.unit.status = BlockedStatus("Failed to bootstrap mysqlrouter")
                    return

                self.model.relations[LEGACY_SHARED_DB][0].data[self.unit].update(
                    {
                        "allowed_units": shared_db_related_unit_name,
                        "db_host": "127.0.0.1",
                        "db_port": "3306",
                        "password": self._get_secret("app", "application_password"),
                        "wait_timeout": "3600",
                    }
                )

            self.unit.status = ActiveStatus()


if __name__ == "__main__":
    main(MySQLRouterOperatorCharm)
