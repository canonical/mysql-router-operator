# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library containing the implementation of the database relation."""

import json
import logging
from typing import Dict

from charms.data_platform_libs.v0.database_requires import (
    DatabaseCreatedEvent,
    DatabaseRequires,
)
from ops.framework import Object

from constants import (
    DATABASE_REQUIRES_RELATION,
    LEGACY_SHARED_DB_DATA,
    MYSQL_ROUTER_DATABASE_DATA,
)

logger = logging.getLogger(__name__)


class DatabaseRequiresRelation(Object):
    """Encapsulation of the relation between mysqlrouter and mysql database."""

    def __init__(self, charm):
        super().__init__(charm, DATABASE_REQUIRES_RELATION)

        self.charm = charm

        # Request a `database` relation if the `shared-db` relation
        # has been formed and the requested database name is available
        shared_db_data = self._get_shared_db_data()
        if shared_db_data:
            self.database = DatabaseRequires(
                self.charm,
                relation_name=DATABASE_REQUIRES_RELATION,
                database_name=shared_db_data["database"],
                extra_user_roles="mysqlrouter",
            )

            self.framework.observe(self.database.on.database_created, self._on_database_created)

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

    # =======================
    #  Handlers
    # =======================

    def _on_database_created(self, event: DatabaseCreatedEvent) -> None:
        """Handle the database created event.

        Set the relation data in the app peer databag for the `shared-db`
        code to be able to bootstrap mysqlrouter, create an application
        user and relay the application user credentials to the consumer application.
        """
        if not self.charm.unit.is_leader():
            return

        self.charm.app_peer_data[MYSQL_ROUTER_DATABASE_DATA] = json.dumps(
            {
                "username": event.username,
                "endpoints": event.endpoints,
            }
        )

        self.charm._set_secret("app", "database_password", event.password)
