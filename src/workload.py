# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Router workload"""

import configparser
import logging
import pathlib
import socket
import string
import typing

import container
import mysql_shell

if typing.TYPE_CHECKING:
    import abstract_charm
    import relations.database_requires

logger = logging.getLogger(__name__)


class Workload:
    """MySQL Router workload"""

    def __init__(self, *, container_: container.Container) -> None:
        self._container = container_
        self._router_data_directory = self._container.path("/var/lib/mysqlrouter")
        self._tls_key_file = self._container.router_config_directory / "custom-key.pem"
        self._tls_certificate_file = (
            self._container.router_config_directory / "custom-certificate.pem"
        )

    @property
    def container_ready(self) -> bool:
        """Whether container is ready

        Only applies to Kubernetes charm
        """
        return self._container.ready

    @property
    def version(self) -> str:
        """MySQL Router version"""
        version = self._container.run_mysql_router(["--version"])
        for component in version.split():
            if component.startswith("8"):
                return component
        return ""

    def disable(self) -> None:
        """Stop and disable MySQL Router service."""
        if not self._container.mysql_router_service_enabled:
            return
        logger.debug("Disabling MySQL Router service")
        self._container.update_mysql_router_service(enabled=False)
        self._container.router_config_directory.rmtree()
        self._container.router_config_directory.mkdir()
        self._router_data_directory.rmtree()
        self._router_data_directory.mkdir()
        logger.debug("Disabled MySQL Router service")

    @property
    def _tls_config_file_data(self) -> str:
        """Render config file template to string.

        Config file enables TLS on MySQL Router.
        """
        template = string.Template(pathlib.Path("templates/tls.cnf").read_text(encoding="utf-8"))
        config_string = template.substitute(
            tls_ssl_key_file=self._tls_key_file,
            tls_ssl_cert_file=self._tls_certificate_file,
        )
        return config_string

    def enable_tls(self, *, key: str, certificate: str):
        """Enable TLS."""
        logger.debug("Enabling TLS")
        self._container.tls_config_file.write_text(self._tls_config_file_data)
        self._tls_key_file.write_text(key)
        self._tls_certificate_file.write_text(certificate)
        logger.debug("Enabled TLS")

    def disable_tls(self) -> None:
        """Disable TLS."""
        logger.debug("Disabling TLS")
        for file in (
            self._container.tls_config_file,
            self._tls_key_file,
            self._tls_certificate_file,
        ):
            file.unlink(missing_ok=True)
        logger.debug("Disabled TLS")


class AuthenticatedWorkload(Workload):
    """Workload with connection to MySQL cluster"""

    def __init__(
        self,
        *,
        container_: container.Container,
        connection_info: "relations.database_requires.ConnectionInformation",
        charm_: "abstract_charm.MySQLRouterCharm",
    ) -> None:
        super().__init__(container_=container_)
        self._connection_info = connection_info
        self._charm = charm_

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

    def _cleanup_after_potential_container_restart(self) -> None:
        """Remove MySQL Router cluster metadata & user after (potential) container restart.

        Only applies to Kubernetes charm

        (Storage is not persisted on container restart—MySQL Router's config file is deleted.
        Therefore, MySQL Router needs to be bootstrapped again.)
        """
        if user_info := self.shell.get_mysql_router_user_for_unit(self._charm.unit.name):
            logger.debug("Cleaning up after container restart")
            self.shell.remove_router_from_cluster_metadata(user_info.router_id)
            self.shell.delete_user(user_info.username)
            logger.debug("Cleaned up after container restart")

    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _get_bootstrap_command(self, password: str) -> typing.List[str]:
        return [
            "--bootstrap",
            self._connection_info.username
            + ":"
            + password
            + "@"
            + self._connection_info.host
            + ":"
            + self._connection_info.port,
            "--strict",
            "--conf-set-option",
            "http_server.bind_address=127.0.0.1",
            "--conf-use-gr-notifications",
        ]

    def _bootstrap_router(self, *, tls: bool) -> None:
        """Bootstrap MySQL Router."""
        logger.debug(
            f"Bootstrapping router {tls=}, {self._connection_info.host=}, {self._connection_info.port=}"
        )
        # Redact password from log
        logged_command = self._get_bootstrap_command("***")

        command = self._get_bootstrap_command(self._connection_info.password)
        try:
            self._container.run_mysql_router(command, timeout=30)
        except container.CalledProcessError as e:
            # Use `logger.error` instead of `logger.exception` so password isn't logged
            logger.error(f"Failed to bootstrap router\n{logged_command=}\nstderr:\n{e.stderr}\n")
            # Original exception contains password
            # Re-raising would log the password to Juju's debug log
            # Raise new exception
            # `from None` disables exception chaining so that the original exception is not
            # included in the traceback
            raise Exception("Failed to bootstrap router") from None
        logger.debug(
            f"Bootstrapped router {tls=}, {self._connection_info.host=}, {self._connection_info.port=}"
        )

    @staticmethod
    def _parse_username_from_config(config_file_text: str) -> str:
        config = configparser.ConfigParser()
        config.read_string(config_file_text)
        return config["metadata_cache:bootstrap"]["user"]

    @property
    def _router_username(self) -> str:
        """Read MySQL Router username from config file.

        During bootstrap, MySQL Router creates a config file which includes a generated username.
        """
        return self._parse_username_from_config(self._container.router_config_file.read_text())

    def enable(self, *, tls: bool, unit_name: str) -> None:
        """Start and enable MySQL Router service."""
        if self._container.mysql_router_service_enabled:
            # If the host or port changes, MySQL Router will receive topology change
            # notifications from MySQL.
            # Therefore, if the host or port changes, we do not need to restart MySQL Router.
            return
        logger.debug("Enabling MySQL Router service")
        self._cleanup_after_potential_container_restart()
        self._bootstrap_router(tls=tls)
        self.shell.add_attributes_to_mysql_router_user(
            username=self._router_username, router_id=self._router_id, unit_name=unit_name
        )
        self._container.update_mysql_router_service(enabled=True, tls=tls)
        logger.debug("Enabled MySQL Router service")
        self._charm.wait_until_mysql_router_ready()

    def _restart(self, *, tls: bool) -> None:
        """Restart MySQL Router to enable or disable TLS."""
        logger.debug("Restarting MySQL Router")
        assert self._container.mysql_router_service_enabled is True
        self._container.update_mysql_router_service(enabled=True, tls=tls)
        logger.debug("Restarted MySQL Router")
        self._charm.wait_until_mysql_router_ready()
        # wait_until_mysql_router_ready will set WaitingStatus—override it with current charm
        # status
        self._charm.set_status(event=None)

    def enable_tls(self, *, key: str, certificate: str):
        """Enable TLS and restart MySQL Router."""
        super().enable_tls(key=key, certificate=certificate)
        if self._container.mysql_router_service_enabled:
            self._restart(tls=True)

    def disable_tls(self) -> None:
        """Disable TLS and restart MySQL Router."""
        super().disable_tls()
        if self._container.mysql_router_service_enabled:
            self._restart(tls=False)
