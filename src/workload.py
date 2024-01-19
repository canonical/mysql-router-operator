# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Router workload"""

import configparser
import logging
import pathlib
import re
import socket
import string
import typing

import ops

import container
import logrotate
import mysql_shell
import server_exceptions

if typing.TYPE_CHECKING:
    import abstract_charm
    import relations.database_requires

logger = logging.getLogger(__name__)


class _NoQuorum(server_exceptions.Error):
    """MySQL Server does not have quorum"""

    MESSAGE = "MySQL Server does not have quorum. Will retry next Juju event"

    def __init__(self):
        super().__init__(ops.WaitingStatus(self.MESSAGE))


class Workload:
    """MySQL Router workload"""

    def __init__(
        self, *, container_: container.Container, logrotate_: logrotate.LogRotate
    ) -> None:
        self._container = container_
        self._logrotate = logrotate_
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
        self._logrotate.disable()
        self._container.router_config_directory.rmtree()
        self._container.router_config_directory.mkdir()
        self._router_data_directory.rmtree()
        self._router_data_directory.mkdir()
        logger.debug("Disabled MySQL Router service")

    def upgrade(self, *, unit: ops.Unit, tls: bool) -> None:
        """Upgrade MySQL Router.

        Only applies to machine charm
        """
        logger.debug("Upgrading MySQL Router")
        self._container.upgrade(unit=unit)
        logger.debug("Upgraded MySQL Router")

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

    @property
    def status(self) -> typing.Optional[ops.StatusBase]:
        """Report non-active status."""
        if not self.container_ready:
            return ops.MaintenanceStatus("Waiting for container")
        if not self._container.mysql_router_service_enabled:
            return ops.WaitingStatus()


class AuthenticatedWorkload(Workload):
    """Workload with connection to MySQL cluster"""

    def __init__(
        self,
        *,
        container_: container.Container,
        logrotate_: logrotate.LogRotate,
        connection_info: "relations.database_requires.CompleteConnectionInformation",
        charm_: "abstract_charm.MySQLRouterCharm",
    ) -> None:
        super().__init__(container_=container_, logrotate_=logrotate_)
        self._connection_info = connection_info
        self._charm = charm_

    @property
    def shell(self) -> mysql_shell.Shell:
        """MySQL Shell"""
        return mysql_shell.Shell(
            _container=self._container, _connection_info=self._connection_info
        )

    @property
    def _router_id(self) -> str:
        """MySQL Router ID in InnoDB Cluster metadata

        Used to remove MySQL Router metadata from InnoDB Cluster
        """
        # MySQL Router is bootstrapped without `--directory`—there is one system-wide instance.
        return f"{socket.getfqdn()}::system"

    def _cleanup_after_upgrade_or_potential_container_restart(self) -> None:
        """Remove Router user after upgrade or (potential) container restart.

        (On Kubernetes, storage is not persisted on container restart—MySQL Router's config file is
        deleted. Therefore, MySQL Router needs to be bootstrapped again.)
        """
        if user_info := self.shell.get_mysql_router_user_for_unit(self._charm.unit.name):
            logger.debug("Cleaning up after upgrade or container restart")
            self.shell.delete_user(user_info.username)
            logger.debug("Cleaned up after upgrade or container restart")

    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _get_bootstrap_command(
        self, connection_info: "relations.database_requires.ConnectionInformation"
    ) -> typing.List[str]:
        return [
            "--bootstrap",
            connection_info.username
            + ":"
            + connection_info.password
            + "@"
            + connection_info.host
            + ":"
            + connection_info.port,
            "--strict",
            "--force",
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
        logged_command = self._get_bootstrap_command(self._connection_info.redacted)

        command = self._get_bootstrap_command(self._connection_info)
        try:
            self._container.run_mysql_router(command, timeout=30)
        except container.CalledProcessError as e:
            # Original exception contains password
            # Re-raising would log the password to Juju's debug log
            # Raise new exception
            # `from None` disables exception chaining so that the original exception is not
            # included in the traceback

            # Use `logger.error` instead of `logger.exception` so password isn't logged
            logger.error(f"Failed to bootstrap router\n{logged_command=}\nstderr:\n{e.stderr}\n")
            stderr = e.stderr.strip()
            if (
                stderr
                == "Error: The provided server is currently not in a InnoDB cluster group with quorum and thus may contain inaccurate or outdated data."
            ):
                logger.error(_NoQuorum.MESSAGE)
                raise _NoQuorum from None
            # Example errors:
            # - "Error: Unable to connect to the metadata server: Error connecting to MySQL server at mysql-k8s-primary.foo1.svc.cluster.local:3306: Can't connect to MySQL server on 'mysql-k8s-primary.foo1.svc.cluster.local:3306' (111) (2003)"
            # - "Error: Unable to connect to the metadata server: Error connecting to MySQL server at mysql-k8s-primary.foo3.svc.cluster.local:3306: Unknown MySQL server host 'mysql-k8s-primary.foo3.svc.cluster.local' (-2) (2005)"
            # Codes 2000-2999 are client errors
            # (https://dev.mysql.com/doc/refman/8.0/en/error-message-elements.html#error-code-ranges)
            elif match := re.fullmatch(r"Error:.*\((?P<code>2[0-9]{3})\)", stderr):
                code = int(match.group("code"))
                if code == 2003:
                    logger.error(server_exceptions.ConnectionError.MESSAGE)
                    raise server_exceptions.ConnectionError from None
                else:
                    logger.error(f"Bootstrap failed with MySQL client error {code}")
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
        self._cleanup_after_upgrade_or_potential_container_restart()
        self._bootstrap_router(tls=tls)
        self.shell.add_attributes_to_mysql_router_user(
            username=self._router_username, router_id=self._router_id, unit_name=unit_name
        )
        self._container.update_mysql_router_service(enabled=True, tls=tls)
        self._logrotate.enable()
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

    @property
    def status(self) -> typing.Optional[ops.StatusBase]:
        """Report non-active status."""
        if status := super().status:
            return status
        if not self.shell.is_router_in_cluster_set(self._router_id):
            # Router should not be removed from ClusterSet after bootstrap (except by MySQL charm
            # when MySQL Router unit departs relation).
            # If Router is not part of ClusterSet after bootstrap, it most likely was manually
            # removed.
            return ops.BlockedStatus(
                "Router was manually removed from MySQL ClusterSet. Remove & re-deploy unit"
            )

    def upgrade(self, *, unit: ops.Unit, tls: bool) -> None:
        enabled = self._container.mysql_router_service_enabled
        if enabled:
            logger.debug("Disabling MySQL Router service before upgrade")
            self.disable()
        super().upgrade(unit=unit, tls=tls)
        if enabled:
            logger.debug("Re-enabling MySQL Router service after upgrade")
            self.enable(tls=tls, unit_name=unit.name)
