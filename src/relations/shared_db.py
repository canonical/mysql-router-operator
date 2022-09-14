# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library containing the implementation of the legacy shared-db relation."""

import json
import logging

from ops.charm import RelationChangedEvent
from ops.framework import Object
from ops.model import Application, BlockedStatus, Unit

from constants import (
    LEGACY_SHARED_DB,
    LEGACY_SHARED_DB_DATA,
    LEGACY_SHARED_DB_DATA_FORWARDED,
    MYSQL_ROUTER_LEADER_BOOTSTRAPED,
    MYSQL_ROUTER_REQUIRES_DATA,
    PASSWORD_LENGTH,
    PEER,
)
from mysql_router_helpers import (
    MySQLRouter,
    MySQLRouterBootstrapError,
    MySQLRouterCreateUserWithDatabasePrivilegesError,
)
from utils import generate_random_password

logger = logging.getLogger(__name__)


class SharedDBRelation(Object):
    """Legacy `shared-db` relation implementation."""

    def __init__(self, charm):
        super().__init__(charm, LEGACY_SHARED_DB)

        self.charm = charm

        self.framework.observe(
            self.charm.on[LEGACY_SHARED_DB].relation_changed, self._on_shared_db_relation_changed
        )
        self.framework.observe(
            self.charm.on[PEER].relation_changed, self._on_peer_relation_changed
        )

    # =======================
    #  Helpers
    # =======================

    def _shared_db_relation_exists(self) -> bool:
        """Indicates whether a shared-db relation exists."""
        shared_db_relations = self.charm.model.relations.get(LEGACY_SHARED_DB)
        return bool(shared_db_relations)

    def _get_related_app_name(self) -> str:
        """Helper to get the name of the related `shared-db` application."""
        if not self._shared_db_relation_exists():
            return None

        for key in self.charm.model.relations[LEGACY_SHARED_DB][0].data:
            if type(key) == Application and key.name != self.charm.app.name:
                return key.name

        return None

    def _get_related_unit_name(self) -> str:
        """Helper to get the name of the related `shared-db` unit."""
        if not self._shared_db_relation_exists():
            return None

        for key in self.charm.model.relations[LEGACY_SHARED_DB][0].data:
            if type(key) == Unit and key.app.name != self.charm.app.name:
                return key.name

        return None

    # =======================
    #  Handlers
    # =======================

    def _on_shared_db_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle the shared-db relation changed event."""
        if not self.charm.unit.is_leader():
            return

        # Forward incoming relation data into the app peer databag
        # (so that the relation with the database can be formed with the appropriate parameters)
        if not self.charm.app_peer_data.get(LEGACY_SHARED_DB_DATA_FORWARDED):
            changed_unit_databag = event.relation.data[event.unit]

            database = changed_unit_databag.get("database")
            hostname = changed_unit_databag.get("hostname")
            username = changed_unit_databag.get("username")

            if not (database and hostname and username):
                logger.debug(
                    "Waiting for `shared-db` databag to be populated by client application"
                )
                event.defer()
                return

            logger.warning("DEPRECATION WARNING - `shared-db` is a legacy interface")

            self.charm.app_peer_data[LEGACY_SHARED_DB_DATA] = json.dumps(
                {
                    "database": database,
                    "hostname": hostname,
                    "username": username,
                }
            )
            self.charm.app_peer_data[LEGACY_SHARED_DB_DATA_FORWARDED] = "true"

    def _on_peer_relation_changed(self, _) -> None:
        """Handler the peer relation changed event.

        Once the `database` relation has been formed, the appropriate database
        credentials will be stored in the app peer databag. These credentials
        can be used to bootstrap mysqlrouter and create the application user.
        """
        if not self.charm.unit.is_leader():
            return

        # Only execute if mysqlrouter has not already been bootstrapped
        if self.charm.app_peer_data.get(MYSQL_ROUTER_LEADER_BOOTSTRAPED):
            return

        if not self.charm.app_peer_data.get(MYSQL_ROUTER_REQUIRES_DATA):
            return

        if not self._shared_db_relation_exists():
            return

        parsed_requires_data = json.loads(self.charm.app_peer_data[MYSQL_ROUTER_REQUIRES_DATA])
        database_password = self.charm._get_secret("app", "database_password")
        parsed_shared_db_data = json.loads(self.charm.app_peer_data[LEGACY_SHARED_DB_DATA])

        db_host = parsed_requires_data["endpoints"].split(",")[0].split(":")[0]
        related_app_name = self._get_related_app_name()
        application_password = generate_random_password(PASSWORD_LENGTH)

        try:
            MySQLRouter.bootstrap_and_start_mysql_router(
                parsed_requires_data["username"],
                database_password,
                related_app_name,
                db_host,
                "3306",
            )
        except MySQLRouterBootstrapError:
            self.charm.unit.status = BlockedStatus("Failed to bootstrap mysqlrouter")
            return

        try:
            MySQLRouter.create_user_with_database_privileges(
                parsed_shared_db_data["username"],
                application_password,
                "%",
                parsed_shared_db_data["database"],
                parsed_requires_data["username"],
                database_password,
                db_host,
                "3306",
            )
        except MySQLRouterCreateUserWithDatabasePrivilegesError:
            self.charm.unit.status = BlockedStatus("Failed to create application user")
            return

        self.charm._set_secret("app", "application_password", application_password)

        unit_databag = self.charm.model.relations[LEGACY_SHARED_DB][0].data[self.charm.unit]
        updates = {
            "allowed_units": self._get_related_unit_name(),
            "db_host": "127.0.0.1",
            "db_port": "3306",
            "password": application_password,
            "wait_timeout": "3600",
        }
        unit_databag.update(updates)

        self.charm.app_peer_data[MYSQL_ROUTER_LEADER_BOOTSTRAPED] = "true"
