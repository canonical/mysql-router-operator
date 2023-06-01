# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Shell in Python execution mode

https://dev.mysql.com/doc/mysql-shell/8.0/en/
"""

import dataclasses
import json
import logging
import secrets
import string

import ops

_PASSWORD_LENGTH = 24
logger = logging.getLogger(__name__)


# TODO python3.10 min version: Add `(kw_only=True)`
@dataclasses.dataclass
class Shell:
    """MySQL Shell connected to MySQL cluster"""

    _container: ops.Container
    username: str
    _password: str
    _host: str
    _port: str

    _TEMPORARY_SCRIPT_FILE = "/tmp/script.py"

    def _run_commands(self, commands: list[str]) -> None:
        """Connect to MySQL cluster and run commands."""
        # Redact password from log
        logged_commands = commands.copy()
        logged_commands.insert(
            0, f"shell.connect('{self.username}:***@{self._host}:{self._port}')"
        )

        commands.insert(
            0, f"shell.connect('{self.username}:{self._password}@{self._host}:{self._port}')"
        )
        self._container.push(self._TEMPORARY_SCRIPT_FILE, "\n".join(commands))
        try:
            process = self._container.exec(
                ["mysqlsh", "--no-wizard", "--python", "--file", self._TEMPORARY_SCRIPT_FILE]
            )
            process.wait_output()
        except ops.pebble.ExecError as e:
            logger.exception(f"Failed to run {logged_commands=}\nstderr:\n{e.stderr}\n")
            raise
        finally:
            self._container.remove_path(self._TEMPORARY_SCRIPT_FILE)

    def _run_sql(self, sql_statements: list[str]) -> None:
        """Connect to MySQL cluster and execute SQL."""
        commands = []
        for statement in sql_statements:
            # Escape double quote (") characters in statement
            statement = statement.replace('"', r"\"")
            commands.append('session.run_sql("' + statement + '")')
        self._run_commands(commands)

    @staticmethod
    def _generate_password() -> str:
        choices = string.ascii_letters + string.digits
        return "".join(secrets.choice(choices) for _ in range(_PASSWORD_LENGTH))

    def _get_attributes(self, additional_attributes: dict = None) -> str:
        """Attributes for (MySQL) users created by this charm

        If the relation with the MySQL charm is broken, the MySQL charm will use this attribute
        to delete all users created by this charm.
        """
        attributes = {"created_by_user": self.username}
        if additional_attributes:
            attributes.update(additional_attributes)
        return json.dumps(attributes)

    def create_application_database_and_user(self, *, username: str, database: str) -> str:
        """Create database and user for related database_provides application."""
        attributes = self._get_attributes()
        logger.debug(f"Creating {database=} and {username=} with {attributes=}")
        password = self._generate_password()
        self._run_sql(
            [
                f"CREATE DATABASE IF NOT EXISTS `{database}`",
                f"CREATE USER `{username}` IDENTIFIED BY '{password}' ATTRIBUTE '{attributes}'",
                f"GRANT ALL PRIVILEGES ON `{database}`.* TO `{username}`",
            ]
        )
        logger.debug(f"Created {database=} and {username=} with {attributes=}")
        return password

    def add_attributes_to_mysql_router_user(
        self, *, username: str, router_id: str, unit_name: str
    ) -> None:
        """Add attributes to user created during MySQL Router bootstrap."""
        attributes = self._get_attributes(
            {"router_id": router_id, "created_by_juju_unit": unit_name}
        )
        logger.debug(f"Adding {attributes=} to {username=}")
        self._run_sql([f"ALTER USER `{username}` ATTRIBUTE '{attributes}'"])
        logger.debug(f"Added {attributes=} to {username=}")

    def delete_user(self, username: str) -> None:
        """Delete user."""
        logger.debug(f"Deleting {username=}")
        self._run_sql([f"DROP USER `{username}`"])
        logger.debug(f"Deleted {username=}")

    def delete_router_user_after_pod_restart(self, router_id: str) -> None:
        """Delete MySQL Router user created by a previous instance of this unit.

        Before pod restart, the charm does not have an opportunity to delete the MySQL Router user.
        During MySQL Router bootstrap, a new user is created. Before bootstrap, the old user
        should be deleted.
        """
        logger.debug(f"Deleting MySQL Router user {router_id=} created by {self.username=}")
        self._run_sql(
            [
                f"SELECT CONCAT('DROP USER ', GROUP_CONCAT(QUOTE(USER), '@', QUOTE(HOST))) INTO @sql FROM INFORMATION_SCHEMA.USER_ATTRIBUTES WHERE ATTRIBUTE->'$.created_by_user'='{self.username}' AND ATTRIBUTE->'$.router_id'='{router_id}'",
                "PREPARE stmt FROM @sql",
                "EXECUTE stmt",
                "DEALLOCATE PREPARE stmt",
            ]
        )
        logger.debug(f"Deleted MySQL Router user {router_id=} created by {self.username=}")

    def remove_router_from_cluster_metadata(self, router_id: str) -> None:
        """Remove MySQL Router from InnoDB Cluster metadata.

        On pod restart, MySQL Router bootstrap will fail without `--force` if cluster metadata
        already exists for the router ID.
        """
        logger.debug(f"Removing {router_id=} from cluster metadata")
        self._run_commands(
            ["cluster = dba.get_cluster()", f'cluster.remove_router_metadata("{router_id}")']
        )
        logger.debug(f"Removed {router_id=} from cluster metadata")
