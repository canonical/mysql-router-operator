#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Application charm that connects to the mysqlrouter charms.

This charm is meant to be used only for testing
the mysqlrouter requires-provides relation.
"""

import itertools
import json
import logging

from charms.data_platform_libs.v0.database_requires import (
    DatabaseCreatedEvent,
    DatabaseRequires,
)
from charms.operator_libs_linux.v1 import systemd
from connector import MySQLConnector
from ops.charm import ActionEvent, CharmBase, StartEvent
from ops.main import main
from ops.model import ActiveStatus, WaitingStatus

from utils import generate_random_chars

logger = logging.getLogger(__name__)

PEER = "application-peers"
REMOTE = "database"
MYSQL_ROUTER_SERVICE_NAME = "mysqlrouter.service"


class ApplicationCharm(CharmBase):
    """Application charm that relates to MySQL Router charm."""

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.start, self._on_start)

        self.database_name = f"{self.app.name.replace('-', '_')}_test_database"
        self.database_requires = DatabaseRequires(self, REMOTE, self.database_name)
        self.framework.observe(
            self.database_requires.on.database_created, self._on_database_created
        )
        self.framework.observe(self.on.get_inserted_data_action, self._get_inserted_data)

    # =======================
    #  Handlers
    # =======================

    def _on_start(self, event: StartEvent) -> None:
        """Handle the start event by setting the charm in waiting status."""
        self.unit.status = WaitingStatus("Waiting for mysqlrouter relation")

        peer_databag = self._peers.data[self.app]
        database_config = peer_databag.get("database_config")
        inserted_value = peer_databag.get("inserted_value")

        if database_config and inserted_value:
            database_config = json.loads(database_config)

            if not systemd.service_running(MYSQL_ROUTER_SERVICE_NAME):
                event.defer()
                return

            with MySQLConnector(database_config) as cursor:
                cursor.execute(
                    (
                        f"SELECT data FROM {self.database_name}.app_data "
                        f"WHERE data = '{inserted_value}'"
                    )
                )
                output = list(itertools.chain(*cursor.fetchall()))

            if output[0] == inserted_value:
                self.unit.status = ActiveStatus()

    def _on_database_created(self, event: DatabaseCreatedEvent) -> None:
        """Handle the database created event."""
        if not self.unit.is_leader():
            return

        logger.info("Received the database created event")

        config = {
            "user": event.username,
            "password": event.password,
            "host": event.endpoints.split(",")[0].split(":")[0],
            "database": self.database_name,
            "raise_on_warnings": False,
        }

        with MySQLConnector(config) as cursor:
            self._create_test_table(cursor)

            random_value = generate_random_chars(255)
            self._insert_test_data(cursor, random_value)

        self._peers.data[self.app]["inserted_value"] = random_value
        self._peers.data[self.app]["database_config"] = json.dumps(config)
        logger.info("Inserted data into the provided database")
        self.unit.status = ActiveStatus()

    def _get_inserted_data(self, event: ActionEvent) -> None:
        app_databag = self._peers.data[self.app]
        event.set_results({"data": app_databag.get("inserted_value")})

    # =======================
    #  Helpers
    # =======================

    def _create_test_table(self, cursor) -> None:
        """Creates a test table in the database."""
        cursor.execute(
            (
                f"CREATE TABLE IF NOT EXISTS {self.database_name}.app_data("
                "id SMALLINT NOT NULL AUTO_INCREMENT, "
                "data VARCHAR(255), "
                "PRIMARY KEY (id))"
            )
        )

    def _insert_test_data(self, cursor, random_value: str) -> None:
        """Inserts the provided random value into the test table in the database."""
        cursor.execute(
            f"INSERT INTO {self.database_name}.app_data(data) VALUES(%s)",
            (random_value,),
        )

    @property
    def _peers(self):
        """Retrieve the peer relation."""
        return self.model.get_relation(PEER)


if __name__ == "__main__":
    main(ApplicationCharm)
