# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library containing the implementation of the database provides relation."""

import json
import logging

from charms.data_platform_libs.v0.database_provides import (
    DatabaseProvides,
    DatabaseRequestedEvent,
)
from ops.framework import Object
from ops.model import Application, BlockedStatus

from constants import (
    CHARMED_MYSQL_COMMON_DIRECTORY,
    DATABASE_PROVIDES_RELATION,
    MYSQL_ROUTER_LEADER_BOOTSTRAPED,
    MYSQL_ROUTER_PROVIDES_DATA,
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


class DatabaseProvidesRelation(Object):
    """Encapsulation of the relation between mysqlrouter and the consumer application."""

    def __init__(self, charm):
        super().__init__(charm, DATABASE_PROVIDES_RELATION)

        self.charm = charm
        self.database = DatabaseProvides(self.charm, relation_name=DATABASE_PROVIDES_RELATION)

        self.framework.observe(self.database.on.database_requested, self._on_database_requested)

        self.framework.observe(
            self.charm.on[PEER].relation_changed, self._on_peer_relation_changed
        )

    # =======================
    #  Helpers
    # =======================

    def _database_provides_relation_exists(self) -> bool:
        database_provides_relations = self.charm.model.relations.get(DATABASE_PROVIDES_RELATION)
        return bool(database_provides_relations)

    def _get_related_app_name(self) -> str:
        """Helper to get the name of the related `database-provides` application."""
        if not self._database_provides_relation_exists():
            return None

        for key in self.charm.model.relations[DATABASE_PROVIDES_RELATION][0].data:
            if type(key) == Application and key.name != self.charm.app.name:
                return key.name

        return None

    # =======================
    #  Handlers
    # =======================

    def _on_database_requested(self, event: DatabaseRequestedEvent) -> None:
        """Handle the database requested event."""
        if not self.charm.unit.is_leader():
            return

        self.charm.app_peer_data[MYSQL_ROUTER_PROVIDES_DATA] = json.dumps(
            {
                "database": event.database,
                "extra_user_roles": event.extra_user_roles,
            }
        )

    def _on_peer_relation_changed(self, _) -> None:
        """Handle the peer relation changed event."""
        if not self.charm.unit.is_leader():
            return

        if self.charm.app_peer_data.get(MYSQL_ROUTER_LEADER_BOOTSTRAPED):
            return

        if not self.charm.app_peer_data.get(MYSQL_ROUTER_REQUIRES_DATA):
            return

        database_provides_relations = self.charm.model.relations.get(DATABASE_PROVIDES_RELATION)
        if not database_provides_relations:
            return

        parsed_database_requires_data = json.loads(
            self.charm.app_peer_data[MYSQL_ROUTER_REQUIRES_DATA]
        )
        parsed_database_provides_data = json.loads(
            self.charm.app_peer_data[MYSQL_ROUTER_PROVIDES_DATA]
        )

        db_host = parsed_database_requires_data["endpoints"].split(",")[0].split(":")[0]
        mysqlrouter_username = parsed_database_requires_data["username"]
        mysqlrouter_user_password = self.charm._get_secret("app", "database-password")
        related_app_name = self._get_related_app_name()

        try:
            MySQLRouter.bootstrap_and_start_mysql_router(
                mysqlrouter_username,
                mysqlrouter_user_password,
                related_app_name,
                db_host,
                "3306",
            )
        except MySQLRouterBootstrapError:
            self.charm.unit.status = BlockedStatus("Failed to bootstrap mysqlrouter")
            return

        provides_relation_id = database_provides_relations[0].id
        application_username = f"application-user-{provides_relation_id}"
        application_password = generate_random_password(PASSWORD_LENGTH)

        try:
            MySQLRouter.create_user_with_database_privileges(
                application_username,
                application_password,
                "%",
                parsed_database_provides_data["database"],
                mysqlrouter_username,
                mysqlrouter_user_password,
                db_host,
                "3306",
            )
        except MySQLRouterCreateUserWithDatabasePrivilegesError:
            self.charm.unit.status = BlockedStatus("Failed to create application user")
            return

        self.charm._set_secret(
            "app", f"application-user-{provides_relation_id}-password", application_password
        )

        self.database.set_credentials(
            provides_relation_id, application_username, application_password
        )
        self.database.set_endpoints(
            provides_relation_id, f"file://{CHARMED_MYSQL_COMMON_DIRECTORY}/var/run/mysqlrouter/mysql.sock"
        )
        self.database.set_read_only_endpoints(
            provides_relation_id, f"file://{CHARMED_MYSQL_COMMON_DIRECTORY}/var/run/mysqlrouter/mysqlro.sock"
        )

        self.charm.app_peer_data[MYSQL_ROUTER_LEADER_BOOTSTRAPED] = "true"
