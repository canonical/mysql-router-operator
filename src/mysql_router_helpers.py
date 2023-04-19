# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper class to manage the MySQL Router lifecycle."""

import logging
import subprocess

import mysql.connector
from charms.operator_libs_linux.v1 import snap

from constants import (
    CHARMED_MYSQL_COMMON_DIRECTORY,
    CHARMED_MYSQL_DATA_DIRECTORY,
    CHARMED_MYSQL_ROUTER,
    CHARMED_MYSQL_ROUTER_SERVICE,
    CHARMED_MYSQL_SNAP,
    CHARMED_MYSQL_SNAP_REVISION,
    SNAP_DAEMON_USER,
)

logger = logging.getLogger(__name__)


class Error(Exception):
    """Base class for exceptions in this module."""

    def __repr__(self):
        """String representation of the Error class."""
        return "<{}.{} {}>".format(type(self).__module__, type(self).__name__, self.args)

    @property
    def name(self):
        """Return a string representation of the model plus class."""
        return "<{}.{}>".format(type(self).__module__, type(self).__name__)

    @property
    def message(self):
        """Return the message passed as an argument."""
        return self.args[0]


class MySQLRouterInstallCharmedMySQLError(Error):
    """Exception raised when there is an issue installing charmed-mysql snap."""


class MySQLRouterBootstrapError(Error):
    """Exception raised when there is an issue bootstrapping MySQLRouter."""


class MySQLRouterCreateUserWithDatabasePrivilegesError(Error):
    """Exception raised when there is an issue creating a database scoped user."""


class MySQLRouter:
    """Class to encapsulate all operations related to MySQLRouter."""

    @staticmethod
    def install_charmed_mysql() -> None:
        """Install charmed-mysql snap and configure MySQLRouter."""
        try:
            logger.debug("Retrieving snap cache")
            cache = snap.SnapCache()
            charmed_mysql = cache[CHARMED_MYSQL_SNAP]

            if not charmed_mysql.present:
                logger.debug("Install charmed-mysql snap")
                charmed_mysql.ensure(snap.SnapState.Latest, revision=CHARMED_MYSQL_SNAP_REVISION)
        except Exception as e:
            logger.exception(f"Failed to install the {CHARMED_MYSQL_SNAP} snap.")
            raise MySQLRouterInstallCharmedMySQLError(e.stderr)

    @staticmethod
    def bootstrap_and_start_mysql_router(
        user,
        password,
        db_host,
        port,
        force=False,
    ) -> None:
        """Bootstrap MySQLRouter and register the service with systemd.

        Args:
            user: The user to connect to the database with
            password: The password to connect to the database with
            db_host: The hostname of the database to connect to
            port: The port at which to bootstrap mysqlrouter to
            force: Overwrite existing config if any

        Raises:
            MySQLRouterBootstrapError - if there is an issue bootstrapping MySQLRouter
        """
        # server_ssl_mode is set to enforce unix_socket connections to be established
        # via encryption (see more at
        # https://dev.mysql.com/doc/refman/8.0/en/caching-sha2-pluggable-authentication.html)
        bootstrap_mysqlrouter_command = [
            "sudo",
            CHARMED_MYSQL_ROUTER,
            "--user",
            SNAP_DAEMON_USER,
            "--bootstrap",
            f"{user}:{password}@{db_host}",
            "--conf-use-sockets",
            "--conf-bind-address",
            "127.0.0.1",
            "--conf-base-port",
            f"{port}",
            "--conf-set-option",
            "DEFAULT.server_ssl_mode=PREFERRED",
            "--conf-set-option",
            "http_server.bind_address=127.0.0.1",
            "--conf-use-gr-notifications",
        ]

        if force:
            bootstrap_mysqlrouter_command.append("--force")

        try:
            subprocess.run(bootstrap_mysqlrouter_command, check=True)

            replace_socket_location_command = [
                "sudo",
                "sed",
                "-Ei",
                f"s:/tmp/(.+).sock:{CHARMED_MYSQL_COMMON_DIRECTORY}/var/run/mysqlrouter/\\1.sock:g",
                f"{CHARMED_MYSQL_DATA_DIRECTORY}/etc/mysqlrouter/mysqlrouter.conf",
            ]
            subprocess.run(replace_socket_location_command, check=True)

            cache = snap.SnapCache()
            charmed_mysql = cache[CHARMED_MYSQL_SNAP]

            charmed_mysql.start(services=[CHARMED_MYSQL_ROUTER_SERVICE])

            if not charmed_mysql.services[CHARMED_MYSQL_ROUTER_SERVICE]["active"]:
                error_message = "Failed to start the mysqlrouter snap service"
                logger.exception(error_message)
                raise MySQLRouterBootstrapError(error_message)
        except subprocess.CalledProcessError as e:
            logger.exception("Failed to bootstrap and start mysqlrouter")
            raise MySQLRouterBootstrapError(e.stderr)
        except snap.SnapError:
            error_message = f"Failed to start snap service {CHARMED_MYSQL_ROUTER_SERVICE}"
            logger.exception(error_message)
            raise MySQLRouterBootstrapError(error_message)

    @staticmethod
    def create_user_with_database_privileges(
        username, password, hostname, database, db_username, db_password, db_host, db_port
    ) -> None:
        """Create a database scope mysql user.

        Args:
            username: Username of the user to create
            password: Password of the user to create
            hostname: Hostname of the user to create
            database: Database that the user should be restricted to
            db_username: The user to connect to the database with
            db_password: The password to use to connect to the database
            db_host: The host name of the database
            db_port: The port for the database

        Raises:
            MySQLRouterCreateUserWithDatabasePrivilegesError -
            when there is an issue creating a database scoped user
        """
        try:
            connection = mysql.connector.connect(
                user=db_username, password=db_password, host=db_host, port=db_port
            )
            cursor = connection.cursor()

            cursor.execute(f"CREATE USER `{username}`@`{hostname}` IDENTIFIED BY '{password}'")
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{database}`.* TO `{username}`@`{hostname}`")

            cursor.close()
            connection.close()
        except mysql.connector.Error as e:
            logger.exception("Failed to create user scoped to a database")
            raise MySQLRouterCreateUserWithDatabasePrivilegesError(e.msg)
