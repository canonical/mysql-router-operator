# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library containing the implementation of the database requires relation."""

import json
import logging
from typing import Dict

from charms.data_platform_libs.v0.database_requires import (
    DatabaseCreatedEvent,
    DatabaseEndpointsChangedEvent,
    DatabaseRequires,
)
from ops.framework import Object
from ops.model import BlockedStatus

from constants import (
    DATABASE_REQUIRES_RELATION,
    LEGACY_SHARED_DB_DATA,
    MYSQL_ROUTER_PROVIDES_DATA,
    MYSQL_ROUTER_REQUIRES_DATA,
)

logger = logging.getLogger(__name__)


class DatabaseRequiresRelation(Object):
    """Encapsulation of the relation between mysqlrouter and mysql database."""

    def __init__(self, charm):
        super().__init__(charm, DATABASE_REQUIRES_RELATION)

        self.charm = charm

        shared_db_data = self._get_shared_db_data()
        provides_data = self._get_provides_data()

        if provides_data and shared_db_data:
            logger.error("Both shared-db and database relations created")
            self.charm.unit.status = BlockedStatus("Both shared-db and database relations exists")
            return

        if not shared_db_data and not provides_data:
            return

        database_name = shared_db_data["database"] if shared_db_data else provides_data["database"]

        self.database_requires_relation = DatabaseRequires(
            self.charm,
            relation_name=DATABASE_REQUIRES_RELATION,
            database_name=database_name,
            extra_user_roles="mysqlrouter",
        )
        self.framework.observe(
            self.database_requires_relation.on.database_created, self._on_database_created
        )
        self.framework.observe(
            self.database_requires_relation.on.endpoints_changed, self._on_endpoints_changed
        )

    # =======================
    #  Helpers
    # =======================

    def _get_shared_db_data(self) -> Dict:
        """Helper to get the `shared-db` relation data from the app peer databag."""
        peers = self.charm._peers
        if not peers:
            return None

        shared_db_data = self.charm.app_peer_data.get(LEGACY_SHARED_DB_DATA)
        if not shared_db_data:
            return None

        return json.loads(shared_db_data)

    def _get_provides_data(self) -> Dict:
        """Helper to get the provides relation data from the app peer databag."""
        peers = self.charm._peers
        if not peers:
            return None

        provides_data = self.charm.app_peer_data.get(MYSQL_ROUTER_PROVIDES_DATA)
        if not provides_data:
            return None

        return json.loads(provides_data)

    # =======================
    #  Handlers
    # =======================

    def _on_database_created(self, event: DatabaseCreatedEvent) -> None:
        """Handle the database created event.

        Set the relation data in the app peer databag for the `shared-db`/`database-provides`
        code to be able to bootstrap mysqlrouter, create an application
        user and relay the application user credentials to the consumer application.
        """
        if not self.charm.unit.is_leader():
            return

        self.charm.app_peer_data[MYSQL_ROUTER_REQUIRES_DATA] = json.dumps(
            {
                "username": event.username,
                "endpoints": event.endpoints,
            }
        )

        self.charm._set_secret("app", "database-password", event.password)

    def _on_endpoints_changed(self, event: DatabaseEndpointsChangedEvent) -> None:
        """Handle the database endpoints changed event.

        Update the MYSQL_ROUTER_REQUIRES_DATA in the app peer databag so that
        bootstraps of future units work.
        """
        if not self.charm.unit.is_leader():
            return

        if self.charm.app_peer_data.get(MYSQL_ROUTER_REQUIRES_DATA):
            requires_data = json.loads(self.charm.app_peer_data[MYSQL_ROUTER_REQUIRES_DATA])

            requires_data["endpoints"] = event.endpoints

            self.charm.app_peer_data[MYSQL_ROUTER_REQUIRES_DATA] = json.dumps(requires_data)
