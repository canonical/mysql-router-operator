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
import typing

import container

_PASSWORD_LENGTH = 24
logger = logging.getLogger(__name__)


# TODO python3.10 min version: Add `(kw_only=True)`
@dataclasses.dataclass
class RouterUserInformation:
    """MySQL Router user information"""

    username: str
    router_id: str


# TODO python3.10 min version: Add `(kw_only=True)`
@dataclasses.dataclass
class Shell:
    """MySQL Shell connected to MySQL cluster"""

    _container: container.Container
    username: str
    _password: str
    _host: str
    _port: str

    def _run_commands(self, commands: list[str]) -> str:
        """Connect to MySQL cluster and run commands."""
        # Redact password from log
        logged_commands = commands.copy()
        # TODO: Password is still logged on user creation
        logged_commands.insert(
            0, f"shell.connect('{self.username}:***@{self._host}:{self._port}')"
        )

        commands.insert(
            0, f"shell.connect('{self.username}:{self._password}@{self._host}:{self._port}')"
        )
        temporary_script_file = self._container.path("/tmp/script.py")
        temporary_script_file.write_text("\n".join(commands))
        try:
            output = self._container.run_mysql_shell(
                [
                    "--no-wizard",
                    "--python",
                    "--file",
                    str(temporary_script_file.relative_to_container),
                ]
            )
        except container.CalledProcessError as e:
            logger.exception(f"Failed to run {logged_commands=}\nstderr:\n{e.stderr}\n")
            raise
        finally:
            temporary_script_file.unlink()
        return output

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

    def get_mysql_router_user_for_unit(
        self, unit_name: str
    ) -> typing.Optional[RouterUserInformation]:
        """Get MySQL Router user created by a previous instance of the unit.

        Get username & router ID attribute.

        Before container restart, the charm does not have an opportunity to delete the MySQL
        Router user or cluster metadata created during MySQL Router bootstrap. After container
        restart, the user and cluster metadata should be deleted before bootstrapping MySQL Router
        again.
        """
        logger.debug(f"Getting MySQL Router user for {unit_name=}")
        rows = json.loads(
            self._run_commands(
                [
                    f"result = session.run_sql(\"SELECT USER, ATTRIBUTE->>'$.router_id' FROM INFORMATION_SCHEMA.USER_ATTRIBUTES WHERE ATTRIBUTE->'$.created_by_user'='{self.username}' AND ATTRIBUTE->'$.created_by_juju_unit'='{unit_name}'\")",
                    "print(result.fetch_all())",
                ]
            )
        )
        if not rows:
            logger.debug(f"No MySQL Router user found for {unit_name=}")
            return
        assert len(rows) == 1
        username, router_id = rows[0]
        user_info = RouterUserInformation(username=username, router_id=router_id)
        logger.debug(f"MySQL Router user found for {unit_name=}: {user_info}")
        return user_info

    def remove_router_from_cluster_metadata(self, router_id: str) -> None:
        """Remove MySQL Router from InnoDB Cluster metadata.

        On container restart, MySQL Router bootstrap will fail without `--force` if cluster
        metadata already exists for the router ID.
        """
        logger.debug(f"Removing {router_id=} from cluster metadata")
        self._run_commands(
            ["cluster = dba.get_cluster()", f'cluster.remove_router_metadata("{router_id}")']
        )
        logger.debug(f"Removed {router_id=} from cluster metadata")

    def delete_user(self, username: str) -> None:
        """Delete user."""
        logger.debug(f"Deleting {username=}")
        self._run_sql([f"DROP USER `{username}`"])
        logger.debug(f"Deleted {username=}")
