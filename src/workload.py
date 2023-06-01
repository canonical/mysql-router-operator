# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Router workload"""

import configparser
import dataclasses
import logging
import pathlib
import socket
import string
import typing

import ops

import mysql_shell

if typing.TYPE_CHECKING:
    import charm
    import relations.database_requires

logger = logging.getLogger(__name__)


# TODO python3.10 min version: Add `(kw_only=True)`
@dataclasses.dataclass
class Workload:
    """MySQL Router workload"""

    _container: ops.Container

    CONTAINER_NAME = "mysql-router"
    _SERVICE_NAME = "mysql_router"
    _UNIX_USERNAME = "mysql"
    _ROUTER_CONFIG_DIRECTORY = pathlib.Path("/etc/mysqlrouter")
    _ROUTER_DATA_DIRECTORY = pathlib.Path("/var/lib/mysqlrouter")
    _ROUTER_CONFIG_FILE = "mysqlrouter.conf"
    _TLS_CONFIG_FILE = "tls.conf"

    @property
    def container_ready(self) -> bool:
        """Whether container is ready"""
        return self._container.can_connect()

    @property
    def _enabled(self) -> bool:
        """Service status"""
        service = self._container.get_services(self._SERVICE_NAME).get(self._SERVICE_NAME)
        if service is None:
            return False
        return service.startup == ops.pebble.ServiceStartup.ENABLED

    @property
    def version(self) -> str:
        """MySQL Router version"""
        process = self._container.exec(["mysqlrouter", "--version"])
        raw_version, _ = process.wait_output()
        for version in raw_version.split():
            if version.startswith("8"):
                return version
        return ""

    def _update_layer(self, *, enabled: bool, tls: bool = None) -> None:
        """Update and restart services.

        Args:
            enabled: Whether MySQL Router service is enabled
            tls: Whether TLS is enabled. Required if enabled=True
        """
        if enabled:
            assert tls is not None, "`tls` argument required when enabled=True"
        command = (
            f"mysqlrouter --config {self._ROUTER_CONFIG_DIRECTORY / self._ROUTER_CONFIG_FILE}"
        )
        if tls:
            command = (
                f"{command} --extra-config {self._ROUTER_CONFIG_DIRECTORY / self._TLS_CONFIG_FILE}"
            )
        if enabled:
            startup = ops.pebble.ServiceStartup.ENABLED.value
        else:
            startup = ops.pebble.ServiceStartup.DISABLED.value
        layer = ops.pebble.Layer(
            {
                "summary": "mysql router layer",
                "description": "the pebble config layer for mysql router",
                "services": {
                    self._SERVICE_NAME: {
                        "override": "replace",
                        "summary": "mysql router",
                        "command": command,
                        "startup": startup,
                        "user": self._UNIX_USERNAME,
                        "group": self._UNIX_USERNAME,
                    },
                },
            }
        )
        self._container.add_layer(self._SERVICE_NAME, layer, combine=True)
        self._container.replan()

    def _create_directory(self, path: pathlib.Path) -> None:
        """Create directory.

        Args:
            path: Full filesystem path
        """
        path = str(path)
        self._container.make_dir(path, user=self._UNIX_USERNAME, group=self._UNIX_USERNAME)

    def _delete_directory(self, path: pathlib.Path) -> None:
        """Delete directory.

        Args:
            path: Full filesystem path
        """
        path = str(path)
        self._container.remove_path(path, recursive=True)

    def disable(self) -> None:
        """Stop and disable MySQL Router service."""
        if not self._enabled:
            return
        logger.debug("Disabling MySQL Router service")
        self._update_layer(enabled=False)
        self._delete_directory(self._ROUTER_CONFIG_DIRECTORY)
        self._create_directory(self._ROUTER_CONFIG_DIRECTORY)
        self._delete_directory(self._ROUTER_DATA_DIRECTORY)
        logger.debug("Disabled MySQL Router service")


# TODO python3.10 min version: Add `(kw_only=True)`
@dataclasses.dataclass
class AuthenticatedWorkload(Workload):
    """Workload with connection to MySQL cluster"""

    _connection_info: "relations.database_requires.ConnectionInformation"
    _charm: "charm.MySQLRouterOperatorCharm"

    _TLS_KEY_FILE = "custom-key.pem"
    _TLS_CERTIFICATE_FILE = "custom-certificate.pem"

    @property
    def shell(self) -> mysql_shell.Shell:
        """MySQL Shell"""
        return mysql_shell.Shell(
            _container=self._container,
            username=self._connection_info.username,
            _password=self._connection_info.password,
            _host=self._connection_info.host,
            _port=self._connection_info.port,
        )

    @property
    def _router_id(self) -> str:
        """MySQL Router ID in InnoDB Cluster metadata

        Used to remove MySQL Router metadata from InnoDB cluster
        """
        # MySQL Router is bootstrapped without `--directory`—there is one system-wide instance.
        return f"{socket.getfqdn()}::system"

    def cleanup_after_pod_restart(self) -> None:
        """Remove MySQL Router cluster metadata & user after pod restart.

        (Storage is not persisted on pod restart—MySQL Router's config file is deleted.
        Therefore, MySQL Router needs to be bootstrapped again.)
        """
        self.shell.remove_router_from_cluster_metadata(self._router_id)
        self.shell.delete_router_user_after_pod_restart(self._router_id)

    def _bootstrap_router(self, *, tls: bool) -> None:
        """Bootstrap MySQL Router and enable service."""
        logger.debug(
            f"Bootstrapping router {tls=}, {self._connection_info.host=}, {self._connection_info.port=}"
        )

        def _get_command(password: str):
            return [
                "mysqlrouter",
                "--bootstrap",
                self._connection_info.username
                + ":"
                + password
                + "@"
                + self._connection_info.host
                + ":"
                + self._connection_info.port,
                "--strict",
                "--user",
                self._UNIX_USERNAME,
                "--conf-set-option",
                "http_server.bind_address=127.0.0.1",
                "--conf-use-gr-notifications",
            ]

        # Redact password from log
        logged_command = _get_command("***")

        command = _get_command(self._connection_info.password)
        try:
            # Bootstrap MySQL Router
            process = self._container.exec(
                command,
                timeout=30,
            )
            process.wait_output()
        except ops.pebble.ExecError as e:
            # Use `logger.error` instead of `logger.exception` so password isn't logged
            logger.error(f"Failed to bootstrap router\n{logged_command=}\nstderr:\n{e.stderr}\n")
            # Original exception contains password
            # Re-raising would log the password to Juju's debug log
            # Raise new exception
            # `from None` disables exception chaining so that the original exception is not
            # included in the traceback
            raise Exception("Failed to bootstrap router") from None
        # Enable service
        self._update_layer(enabled=True, tls=tls)

        logger.debug(
            f"Bootstrapped router {tls=}, {self._connection_info.host=}, {self._connection_info.port=}"
        )

    @property
    def _router_username(self) -> str:
        """Read MySQL Router username from config file.

        During bootstrap, MySQL Router creates a config file at
        `/etc/mysqlrouter/mysqlrouter.conf`. This file contains the username that was created
        during bootstrap.
        """
        config = configparser.ConfigParser()
        config.read_file(
            self._container.pull(self._ROUTER_CONFIG_DIRECTORY / self._ROUTER_CONFIG_FILE)
        )
        return config["metadata_cache:bootstrap"]["user"]

    def enable(self, *, tls: bool, unit_name: str) -> None:
        """Start and enable MySQL Router service."""
        if self._enabled:
            # If the host or port changes, MySQL Router will receive topology change
            # notifications from MySQL.
            # Therefore, if the host or port changes, we do not need to restart MySQL Router.
            return
        logger.debug("Enabling MySQL Router service")
        self._bootstrap_router(tls=tls)
        self.shell.add_attributes_to_mysql_router_user(
            username=self._router_username, router_id=self._router_id, unit_name=unit_name
        )
        logger.debug("Enabled MySQL Router service")
        self._charm.wait_until_mysql_router_ready()

    def _restart(self, *, tls: bool) -> None:
        """Restart MySQL Router to enable or disable TLS."""
        logger.debug("Restarting MySQL Router")
        assert self._enabled is True
        self._bootstrap_router(tls=tls)
        logger.debug("Restarted MySQL Router")
        self._charm.wait_until_mysql_router_ready()
        # wait_until_mysql_router_ready will set WaitingStatus—override it with current charm
        # status
        self._charm.set_status(event=None)

    def _write_file(self, path: pathlib.Path, content: str) -> None:
        """Write content to file.

        Args:
            path: Full filesystem path (with filename)
            content: File content
        """
        self._container.push(
            str(path),
            content,
            permissions=0o600,
            user=self._UNIX_USERNAME,
            group=self._UNIX_USERNAME,
        )
        logger.debug(f"Wrote file {path=}")

    def _delete_file(self, path: pathlib.Path) -> None:
        """Delete file.

        Args:
            path: Full filesystem path (with filename)
        """
        path = str(path)
        if self._container.exists(path):
            self._container.remove_path(path)
            logger.debug(f"Deleted file {path=}")

    @property
    def _tls_config_file(self) -> str:
        """Render config file template to string.

        Config file enables TLS on MySQL Router.
        """
        with open("templates/tls.cnf", "r") as template_file:
            template = string.Template(template_file.read())
        config_string = template.substitute(
            tls_ssl_key_file=self._ROUTER_CONFIG_DIRECTORY / self._TLS_KEY_FILE,
            tls_ssl_cert_file=self._ROUTER_CONFIG_DIRECTORY / self._TLS_CERTIFICATE_FILE,
        )
        return config_string

    def enable_tls(self, *, key: str, certificate: str):
        """Enable TLS and restart MySQL Router."""
        logger.debug("Enabling TLS")
        self._write_file(
            self._ROUTER_CONFIG_DIRECTORY / self._TLS_CONFIG_FILE, self._tls_config_file
        )
        self._write_file(self._ROUTER_CONFIG_DIRECTORY / self._TLS_KEY_FILE, key)
        self._write_file(self._ROUTER_CONFIG_DIRECTORY / self._TLS_CERTIFICATE_FILE, certificate)
        if self._enabled:
            self._restart(tls=True)
        logger.debug("Enabled TLS")

    def disable_tls(self) -> None:
        """Disable TLS and restart MySQL Router."""
        logger.debug("Disabling TLS")
        for file in (self._TLS_CONFIG_FILE, self._TLS_KEY_FILE, self._TLS_CERTIFICATE_FILE):
            self._delete_file(self._ROUTER_CONFIG_DIRECTORY / file)
        if self._enabled:
            self._restart(tls=False)
        logger.debug("Disabled TLS")
