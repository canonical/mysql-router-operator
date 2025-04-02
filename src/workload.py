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

import charm_refresh
import ops
import requests
import tenacity

import container
import mysql_shell
import server_exceptions

if typing.TYPE_CHECKING:
    import abstract_charm
    import logrotate
    import relations.cos
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
        self,
        *,
        container_: container.Container,
        logrotate_: "logrotate.LogRotate",
        cos: "relations.cos.COSRelation",
    ) -> None:
        self._container = container_
        self._logrotate = logrotate_
        self._cos = cos
        self._router_data_directory = self._container.path("/var/lib/mysqlrouter")
        self._tls_key_file = self._container.router_config_directory / "custom-key.pem"
        self._tls_certificate_file = (
            self._container.router_config_directory / "custom-certificate.pem"
        )
        self._tls_certificate_authority_file = (
            self._container.router_config_directory / "custom-certificate-authority.pem"
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

    def install(
        self,
        *,
        unit: ops.Unit,
        model_uuid: str,
        snap_revision: str,
        refresh: charm_refresh.Machines,
    ) -> None:
        """Ensure snap is installed by this charm

        Only applies to machine charm

        If snap is not installed, install it
        If snap is installed, check that it was installed by this charm & raise an exception otherwise

        Automatically retries if snap installation fails
        """
        self._container.install(
            unit=unit, model_uuid=model_uuid, snap_revision=snap_revision, refresh=refresh
        )

    def refresh(
        self,
        *,
        event,
        unit: ops.Unit,
        model_uuid: str,
        snap_revision: str,
        refresh: charm_refresh.Machines,
        tls: bool,
        exporter_config: "relations.cos.ExporterConfig",
    ) -> None:
        """Refresh MySQL Router

        Only applies to machine charm
        """
        self._container.refresh(
            unit=unit, model_uuid=model_uuid, snap_revision=snap_revision, refresh=refresh
        )

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

    @property
    def _custom_certificate(self) -> typing.Optional[str]:
        """Whether custom TLS certs are enabled for MySQL Router"""
        if self._tls_key_file.exists() and self._tls_certificate_file.exists():
            return self._tls_certificate_file.read_text()

    def cleanup_monitoring_user(self) -> None:
        """Clean up router REST API user for mysqlrouter exporter."""
        logger.debug("Cleaning router REST API user for mysqlrouter exporter")
        self._container.set_mysql_router_rest_api_password(
            user=self._cos.MONITORING_USERNAME,
            password=None,
        )
        self._cos._reset_monitoring_password()
        logger.debug("Cleaned router REST API user for mysqlrouter exporter")

    def _disable_exporter(self) -> None:
        """Stop and disable MySQL Router exporter service, keeping router enabled."""
        logger.debug("Disabling MySQL Router exporter service")
        self._container.update_mysql_router_exporter_service(enabled=False)
        self.cleanup_monitoring_user()
        logger.debug("Disabled MySQL Router exporter service")

    def _enable_tls(self, *, key: str, certificate: str, certificate_authority: str) -> None:
        """Enable TLS."""
        logger.debug("Creating TLS files")
        self._container.tls_config_file.write_text(self._tls_config_file_data)
        self._tls_key_file.write_text(key)
        self._tls_certificate_file.write_text(certificate)
        self._tls_certificate_authority_file.write_text(certificate_authority)
        logger.debug("Created TLS files")

    def _disable_tls(self) -> None:
        """Disable TLS."""
        logger.debug("Deleting TLS files")
        for file in (
            self._container.tls_config_file,
            self._tls_key_file,
            self._tls_certificate_file,
        ):
            file.unlink(missing_ok=True)
        logger.debug("Deleted TLS files")

    def _disable_router(self) -> None:
        """Disable router and clean up corresponding router files."""
        logger.info("Disabling MySQL Router service")
        self._container.update_mysql_router_service(enabled=False)
        self._logrotate.disable()
        self._container.router_config_directory.rmtree()
        self._container.router_config_directory.mkdir()
        self._router_data_directory.rmtree()
        self._router_data_directory.mkdir()
        logger.info("Disabled MySQL Router service")

    def reconcile(
        self,
        *,
        event,
        tls: bool,
        unit_name: str,
        exporter_config: "relations.cos.ExporterConfig",
        key: str = None,
        certificate: str = None,
        certificate_authority: str = None,
    ) -> None:
        """Reconcile all workloads (router, exporter, tls)."""
        if tls and not (key and certificate and certificate_authority):
            raise ValueError("`key` and `certificate` arguments required when tls=True")

        if self._container.mysql_router_service_enabled:
            self._disable_router()

        if self._container.mysql_router_exporter_service_enabled:
            self._disable_exporter()

        self._disable_tls()

    @property
    def status(self) -> typing.Optional[ops.StatusBase]:
        """Report non-active status."""
        if not self.container_ready:
            return ops.MaintenanceStatus("Waiting for container")
        if not self._container.mysql_router_service_enabled:
            return ops.WaitingStatus()


class RunningWorkload(Workload):
    """Workload with connection to MySQL cluster"""

    def __init__(
        self,
        *,
        container_: container.Container,
        logrotate_: "logrotate.LogRotate",
        connection_info: "relations.database_requires.CompleteConnectionInformation",
        cos: "relations.cos.COSRelation",
        charm_: "abstract_charm.MySQLRouterCharm",
    ) -> None:
        super().__init__(container_=container_, logrotate_=logrotate_, cos=cos)
        self._connection_info = connection_info
        self._cos = cos
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
        self, *, event, connection_info: "relations.database_requires.ConnectionInformation"
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
            "--conf-set-option",
            "http_auth_backend:default_auth_backend.backend=file",
            "--conf-set-option",
            f"http_auth_backend:default_auth_backend.filename={self._container.rest_api_credentials_file.relative_to_container}",
            "--conf-use-gr-notifications",
        ]

    def _bootstrap_router(self, *, event, tls: bool) -> None:
        """Bootstrap MySQL Router."""
        logger.debug(
            f"Bootstrapping router {tls=}, {self._connection_info.host=}, {self._connection_info.port=}"
        )
        # Redact password from log
        logged_command = self._get_bootstrap_command(
            event=event, connection_info=self._connection_info.redacted
        )

        command = self._get_bootstrap_command(event=event, connection_info=self._connection_info)
        try:
            self._container.run_mysql_router(command)
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
                    logger.error(server_exceptions.ConnectionError_.MESSAGE)
                    raise server_exceptions.ConnectionError_ from None
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

    def _restart(self, *, event, tls: bool) -> None:
        """Restart MySQL Router to enable or disable TLS."""
        logger.debug("Restarting MySQL Router")
        assert self._container.mysql_router_service_enabled is True
        self._container.update_mysql_router_service(enabled=True, tls=tls)
        logger.debug("Restarted MySQL Router")
        self._charm.wait_until_mysql_router_ready(event=event)
        # wait_until_mysql_router_ready will set WaitingStatus—override it with current charm
        # status
        self._charm.set_status(event=None)

    def _enable_router(self, *, event, tls: bool, unit_name: str) -> None:
        """Enable router after setting up all the necessary prerequisites."""
        logger.info("Enabling MySQL Router service")
        self._cleanup_after_upgrade_or_potential_container_restart()
        # create an empty credentials file, if the file does not exist
        self._container.create_router_rest_api_credentials_file()
        self._bootstrap_router(event=event, tls=tls)
        self.shell.add_attributes_to_mysql_router_user(
            username=self._router_username, router_id=self._router_id, unit_name=unit_name
        )
        self._container.update_mysql_router_service(enabled=True, tls=tls)
        self._logrotate.enable()
        logger.info("Enabled MySQL Router service")
        self._charm.wait_until_mysql_router_ready(event=event)

    def _enable_exporter(
        self, *, tls: bool, exporter_config: "relations.cos.ExporterConfig"
    ) -> None:
        """Enable the mysqlrouter exporter."""
        logger.debug("Enabling MySQL Router exporter service")
        self.setup_monitoring_user()
        self._container.update_mysql_router_exporter_service(
            enabled=True,
            config=exporter_config,
            tls=tls,
            key_filename=str(self._tls_key_file),
            certificate_filename=str(self._tls_certificate_file),
            certificate_authority_filename=str(self._tls_certificate_authority_file),
        )
        logger.debug("Enabled MySQL Router exporter service")

    def reconcile(
        self,
        *,
        event,
        tls: bool,
        unit_name: str,
        exporter_config: "relations.cos.ExporterConfig",
        key: str = None,
        certificate: str = None,
        certificate_authority: str = None,
    ) -> None:
        """Reconcile all workloads (router, exporter, tls)."""
        if tls and not (key and certificate and certificate_authority):
            raise ValueError(
                "`key`, `certificate`, and `certificate_authority` arguments required when tls=True"
            )

        # If the host or port changes, MySQL Router will receive topology change
        # notifications from MySQL.
        # Therefore, if the host or port changes, we do not need to restart MySQL Router.
        is_charm_exposed = self._charm.is_externally_accessible(event=event)
        socket_file_exists = self._container.path("/run/mysqlrouter/mysql.sock").exists()
        require_rebootstrap = is_charm_exposed == socket_file_exists
        if require_rebootstrap:
            self._disable_router()

        # `self._custom_certificate` will change after we enable/disable TLS
        custom_certificate = self._custom_certificate
        if tls:
            self._enable_tls(
                key=key, certificate=certificate, certificate_authority=certificate_authority
            )
            if custom_certificate != certificate and self._container.mysql_router_service_enabled:
                self._restart(event=event, tls=tls)
        else:
            self._disable_tls()
            if custom_certificate and self._container.mysql_router_service_enabled:
                self._restart(event=event, tls=tls)

        if not self._container.mysql_router_service_enabled:
            self._enable_router(event=event, tls=tls, unit_name=unit_name)

        if (not self._container.mysql_router_exporter_service_enabled and exporter_config) or (
            self._container.mysql_router_exporter_service_enabled
            and custom_certificate != certificate
        ):
            self._enable_exporter(tls=tls, exporter_config=exporter_config)
        elif self._container.mysql_router_exporter_service_enabled and not exporter_config:
            self._disable_exporter()

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

    def refresh(
        self,
        *,
        event,
        unit: ops.Unit,
        model_uuid: str,
        snap_revision: str,
        refresh: charm_refresh.Machines,
        tls: bool,
        exporter_config: "relations.cos.ExporterConfig",
    ) -> None:
        enabled = self._container.mysql_router_service_enabled
        exporter_enabled = self._container.mysql_router_exporter_service_enabled
        if exporter_enabled:
            self._disable_exporter()
        if enabled:
            logger.debug("Disabling MySQL Router service before upgrade")
            self._disable_router()
        try:
            super().refresh(
                event=event,
                unit=unit,
                model_uuid=model_uuid,
                snap_revision=snap_revision,
                refresh=refresh,
                tls=tls,
                exporter_config=exporter_config,
            )
        except container.RefreshFailed:
            message = "Re-enabling MySQL Router service after failed snap refresh"
            raise
        else:
            message = "Re-enabling MySQL Router service after refresh"
        finally:
            if enabled:
                logger.debug(message)
                self._enable_router(event=event, tls=tls, unit_name=unit.name)
            if exporter_enabled:
                self._enable_exporter(tls=tls, exporter_config=exporter_config)

    def _wait_until_http_server_authenticates(self) -> None:
        """Wait until active connection with router HTTP server using monitoring credentials."""
        logger.debug("Waiting until router HTTP server authenticates")
        try:
            for attempt in tenacity.Retrying(
                retry=tenacity.retry_if_exception_type(RuntimeError)
                | tenacity.retry_if_exception_type(requests.exceptions.HTTPError),
                reraise=True,
                stop=tenacity.stop_after_delay(30),
                wait=tenacity.wait_fixed(5),
            ):
                with attempt:
                    response = requests.get(
                        f"https://127.0.0.1:{self._cos.HTTP_SERVER_PORT}/api/20190715/routes",
                        auth=(self._cos.MONITORING_USERNAME, self._cos.get_monitoring_password()),
                        verify=False,  # do not verify tls certs as default certs do not have 127.0.0.1 in its list of IP SANs
                    )
                    response.raise_for_status()
                    if "bootstrap_rw" not in response.text:
                        raise RuntimeError("Invalid response from router's HTTP server")
        except (requests.exceptions.HTTPError, RuntimeError):
            logger.exception("Unable to authenticate router HTTP server")
            raise
        else:
            logger.debug("Successfully authenticated router HTTP server")

    def setup_monitoring_user(self) -> None:
        """Set up a router REST API use for mysqlrouter exporter."""
        logger.debug("Setting up router REST API user for mysqlrouter exporter")
        self._container.set_mysql_router_rest_api_password(
            user=self._cos.MONITORING_USERNAME,
            password=self._cos.get_monitoring_password(),
        )
        self._wait_until_http_server_authenticates()
        logger.debug("Set up router REST API user for mysqlrouter exporter")
