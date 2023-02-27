# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper class to manage the MySQL Router lifecycle."""

import grp
import logging
import os
import pwd
import subprocess

import jinja2
import mysql.connector
from charms.operator_libs_linux.v0 import apt, passwd
from charms.operator_libs_linux.v1 import systemd

from constants import (
    MYSQL_HOME_DIRECTORY,
    MYSQL_ROUTER_APT_PACKAGE,
    MYSQL_ROUTER_GROUP,
    MYSQL_ROUTER_SERVICE_NAME,
    MYSQL_ROUTER_SYSTEMD_DIRECTORY,
    MYSQL_ROUTER_UNIT_TEMPLATE,
    MYSQL_ROUTER_USER,
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


class MySQLRouterInstallAndConfigureError(Error):
    """Exception raised when there is an issue installing MySQLRouter."""


class MySQLRouterBootstrapError(Error):
    """Exception raised when there is an issue bootstrapping MySQLRouter."""


class MySQLRouterCreateUserWithDatabasePrivilegesError(Error):
    """Exception raised when there is an issue creating a database scoped user."""


class MySQLRouter:
    """Class to encapsulate all operations related to MySQLRouter."""

    @staticmethod
    def install_and_configure_mysql_router() -> None:
        """Install and configure MySQLRouter."""
        try:
            apt.update()
            apt.add_package(MYSQL_ROUTER_APT_PACKAGE)

            if not passwd.group_exists(MYSQL_ROUTER_GROUP):
                passwd.add_group(MYSQL_ROUTER_GROUP, system_group=True)

            if not passwd.user_exists(MYSQL_ROUTER_USER):
                passwd.add_user(
                    MYSQL_ROUTER_USER,
                    shell="/usr/sbin/nologin",
                    system_user=True,
                    primary_group=MYSQL_ROUTER_GROUP,
                    home_dir=MYSQL_HOME_DIRECTORY,
                )

            if not os.path.exists(MYSQL_HOME_DIRECTORY):
                os.makedirs(MYSQL_HOME_DIRECTORY, mode=0o755, exist_ok=True)

                user_id = pwd.getpwnam(MYSQL_ROUTER_USER).pw_uid
                group_id = grp.getgrnam(MYSQL_ROUTER_GROUP).gr_gid

                os.chown(MYSQL_HOME_DIRECTORY, user_id, group_id)
        except Exception as e:
            logger.exception(
                f"Failed to install the {MYSQL_ROUTER_APT_PACKAGE} apt package.", exc_info=e
            )
            raise MySQLRouterInstallAndConfigureError(e.stderr)

    @staticmethod
    def _render_and_copy_mysqlrouter_systemd_unit_file(app_name):
        with open(MYSQL_ROUTER_UNIT_TEMPLATE, "r") as file:
            template = jinja2.Template(file.read())

        rendered_template = template.render(charm_app_name=app_name)
        systemd_file_path = f"{MYSQL_ROUTER_SYSTEMD_DIRECTORY}/mysqlrouter.service"

        with open(systemd_file_path, "w+") as file:
            file.write(rendered_template)

        os.chmod(systemd_file_path, 0o644)
        mysql_user = pwd.getpwnam(MYSQL_ROUTER_USER)
        os.chown(systemd_file_path, uid=mysql_user.pw_uid, gid=mysql_user.pw_gid)

    @staticmethod
    def bootstrap_and_start_mysql_router(
        user,
        password,
        name,
        db_host,
        port,
        force=False,
    ) -> None:
        """Bootstrap MySQLRouter and register the service with systemd.

        Args:
            user: The user to connect to the database with
            password: The password to connect to the database with
            name: The name of application that will use mysqlrouter
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
            "/usr/bin/mysqlrouter",
            "--user",
            MYSQL_ROUTER_USER,
            "--name",
            name,
            "--bootstrap",
            f"{user}:{password}@{db_host}",
            "--directory",
            f"{MYSQL_HOME_DIRECTORY}/{name}",
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
            subprocess.check_output(bootstrap_mysqlrouter_command, stderr=subprocess.STDOUT)
            MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file(name)

            if not systemd.daemon_reload():
                logger.exception("Failed to load the mysqlrouter systemd service")
                raise MySQLRouterBootstrapError("Failed to load mysqlrouter systemd service")

            systemd.service_start(MYSQL_ROUTER_SERVICE_NAME)
            if not MySQLRouter.is_mysqlrouter_running():
                logger.exception("Failed to start the mysqlrouter systemd service")
                raise MySQLRouterBootstrapError("Failed to start the mysqlrouter systemd service")
        except subprocess.CalledProcessError as e:
            logger.exception("Failed to bootstrap mysqlrouter", exc_info=e)
            raise MySQLRouterBootstrapError(e.stderr)
        except systemd.SystemdError as e:
            logger.exception("Failed to set up mysqlrouter as a systemd service", exc_info=e)
            raise MySQLRouterBootstrapError("Failed to set up mysqlrouter as a systemd service")

    @staticmethod
    def is_mysqlrouter_running() -> bool:
        """Indicates whether MySQLRouter is running as a systemd service."""
        return systemd.service_running(MYSQL_ROUTER_SERVICE_NAME)

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
            logger.exception("Failed to create user scoped to a database", exc_info=e)
            raise MySQLRouterCreateUserWithDatabasePrivilegesError(e.msg)
