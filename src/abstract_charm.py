# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Router charm"""

import abc
import logging
import socket
import typing

import charms.data_platform_libs.v0.data_secrets as secrets
import ops
import tenacity

import container
import lifecycle
import logrotate
import machine_upgrade
import relations.database_provides
import relations.database_requires
import server_exceptions
import upgrade
import workload

logger = logging.getLogger(__name__)


class MySQLRouterSecretsError(Exception):
    """MySQLRouter secrets related error."""


class MySQLRouterCharm(ops.CharmBase, abc.ABC):
    """MySQL Router charm"""

    _PEER_RELATION_NAME = "mysql-router-peers"

    def __init__(self, *args) -> None:
        super().__init__(*args)
        # Instantiate before registering other event observers
        self._unit_lifecycle = lifecycle.Unit(
            self, subordinated_relation_endpoint_names=self._subordinate_relation_endpoint_names
        )
        self._secrets = secrets.SecretCache(self)

        self._workload_type = workload.Workload
        self._authenticated_workload_type = workload.AuthenticatedWorkload
        self._database_requires = relations.database_requires.RelationEndpoint(self)
        self.framework.observe(self.on.update_status, self.reconcile)
        self.framework.observe(
            self.on[upgrade.PEER_RELATION_ENDPOINT_NAME].relation_changed, self.reconcile
        )
        self.framework.observe(
            self.on[upgrade.RESUME_ACTION_NAME].action, self._on_resume_upgrade_action
        )
        # (For Kubernetes) Reset partition after scale down
        self.framework.observe(
            self.on[upgrade.PEER_RELATION_ENDPOINT_NAME].relation_departed, self.reconcile
        )
        # Handle upgrade & set status on first start if no relations active
        self.framework.observe(self.on.start, self.reconcile)
        # Update app status
        self.framework.observe(self.on.leader_elected, self.reconcile)
        # Set versions in upgrade peer relation app databag
        self.framework.observe(
            self.on[upgrade.PEER_RELATION_ENDPOINT_NAME].relation_created,
            self._upgrade_relation_created,
        )

    @property
    @abc.abstractmethod
    def _subordinate_relation_endpoint_names(self) -> typing.Optional[typing.Iterable[str]]:
        """Subordinate relation endpoint names

        Does NOT include relations where charm is principal
        """

    @property
    @abc.abstractmethod
    def _container(self) -> container.Container:
        """Workload container (snap or ROCK)"""

    @property
    @abc.abstractmethod
    def _upgrade(self) -> typing.Optional[upgrade.Upgrade]:
        pass

    @property
    @abc.abstractmethod
    def _logrotate(self) -> logrotate.LogRotate:
        """logrotate"""

    @property
    @abc.abstractmethod
    def _read_write_endpoint(self) -> str:
        """MySQL Router read-write endpoint"""

    @property
    @abc.abstractmethod
    def _read_only_endpoint(self) -> str:
        """MySQL Router read-only endpoint"""

    @property
    def peers(self) -> typing.Optional[ops.model.Relation]:
        """Retrieve the peer relation."""
        return self.model.get_relation(self._PEER_RELATION_NAME)

    def get_workload(self, *, event):
        """MySQL Router workload"""
        if connection_info := self._database_requires.get_connection_info(event=event):
            return self._authenticated_workload_type(
                container_=self._container,
                logrotate_=self._logrotate,
                connection_info=connection_info,
                cos_=self._cos,
                charm_=self,
            )
        return self._workload_type(
            container_=self._container, logrotate_=self._logrotate, cos_=self._cos
        )

    @staticmethod
    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _prioritize_statuses(statuses: typing.List[ops.StatusBase]) -> ops.StatusBase:
        """Report the highest priority status.

        (Statuses of the same type are reported in the order they were added to `statuses`)
        """
        status_priority = (
            ops.BlockedStatus,
            ops.MaintenanceStatus,
            ops.WaitingStatus,
            # Catch any unknown status type
            ops.StatusBase,
        )
        for status_type in status_priority:
            for status in statuses:
                if isinstance(status, status_type):
                    return status
        return ops.ActiveStatus()

    def _determine_app_status(self, *, event) -> ops.StatusBase:
        """Report app status."""
        if self._upgrade and (upgrade_status := self._upgrade.app_status):
            # Upgrade status should take priority over relation status—even if the status level is
            # normally lower priority.
            # (Relations should not be modified during upgrade.)
            return upgrade_status
        statuses = []
        for endpoint in (self._database_requires, self._database_provides):
            if status := endpoint.get_status(event):
                statuses.append(status)
        return self._prioritize_statuses(statuses)

    def _determine_unit_status(self, *, event) -> ops.StatusBase:
        """Report unit status."""
        statuses = []
        workload_status = self.get_workload(event=event).status
        if self._upgrade:
            statuses.append(self._upgrade.get_unit_juju_status(workload_status=workload_status))
        statuses.append(workload_status)
        return self._prioritize_statuses(statuses)

    def set_status(self, *, event, app=True, unit=True) -> None:
        """Set charm status."""
        if app and self._unit_lifecycle.authorized_leader:
            self.app.status = self._determine_app_status(event=event)
            logger.debug(f"Set app status to {self.app.status}")
        if unit:
            self.unit.status = self._determine_unit_status(event=event)
            logger.debug(f"Set unit status to {self.unit.status}")

    def wait_until_mysql_router_ready(self) -> None:
        """Wait until a connection to MySQL Router is possible.

        Retry every 5 seconds for up to 30 seconds.
        """
        logger.debug("Waiting until MySQL Router is ready")
        self.unit.status = ops.MaintenanceStatus("MySQL Router starting")
        try:
            for attempt in tenacity.Retrying(
                reraise=True,
                stop=tenacity.stop_after_delay(30),
                wait=tenacity.wait_fixed(5),
            ):
                with attempt:
                    for port in (6446, 6447):
                        with socket.socket() as s:
                            assert s.connect_ex(("localhost", port)) == 0
        except AssertionError:
            logger.exception("Unable to connect to MySQL Router")
            raise
        else:
            logger.debug("MySQL Router is ready")

    def _scope_obj(self, scope: secrets.Scopes) -> dict:
        """Return corresponding data unit for app/unit."""
        if scope == secrets.APP_SCOPE:
            return self.app
        if scope == secrets.UNIT_SCOPE:
            return self.unit

    def _peer_data(self, scope: secrets.Scopes) -> dict:
        """Return corresponding databag for app/unit."""
        if self.peers is None:
            return {}
        return self.peers.data[self._scope_obj(scope)]

    def _get_secret_from_juju(self, scope: secrets.Scopes, key: str) -> typing.Optional[str]:
        """Retrieve and return the secret from the juju secret storage."""
        label = secrets.generate_secret_label(self, scope)
        secret = self._secrets.get(label)

        if not secret:
            logger.debug("Getting a secret when secret is not added in juju")
            return

        value = secret.get_content().get(key)
        logger.debug(f"Retrieved secret {key} for unit from juju")
        return value

    def _get_secret_from_databag(self, scope: secrets.Scopes, key: str) -> typing.Optional[str]:
        """Retrieve and return the secret from the peer relation databag."""
        return self._peer_data(scope).get(key)

    def get_secret(self, scope: secrets.Scopes, key: str) -> typing.Optional[str]:
        """Get secret from the secret storage.

        Retrieve secret from juju secrets backend if secret exists there.
        Else retrieve from peer databag. This is to account for cases where
        secrets are stored in peer databag but the charm is then refreshed to
        a newer revision.
        """
        if scope not in [secrets.APP_SCOPE, secrets.UNIT_SCOPE]:
            raise MySQLRouterSecretsError(f"Invalid secret scope: {scope}")

        if ops.jujuversion.JujuVersion.from_environ().has_secrets:
            secret = self._get_secret_from_juju(scope, key)
            if secret:
                return secret

        return self._get_secret_from_databag(scope, key)

    def _set_secret_in_juju(
        self, scope: secrets.Scopes, key: str, value: typing.Optional[str]
    ) -> None:
        """Set the secret in the juju secret storage."""
        # Charm could have been upgraded since last run
        # We make an attempt to remove potential traces from the databag
        self._peer_data(scope).pop(key, None)

        label = secrets.generate_secret_label(self, scope)
        secret = self._secrets.get(label)
        if not secret and value:
            self._secrets.add(label, {key: value}, scope)
            return

        content = secret.get_content() if secret else None

        if not value:
            if content and key in content:
                content.pop(key, None)
            else:
                logger.error(f"Non-existing secret {scope}:{key} was attempted to be removed.")
                return
        else:
            content.update({key: value})

        secret.set_content(content)

    def _set_secret_in_databag(
        self, scope: secrets.Scopes, key: str, value: typing.Optional[str]
    ) -> None:
        """Set secret in the peer relation databag."""
        if not value:
            try:
                self._peer_data(scope).pop(key)
                return
            except KeyError:
                logger.error(f"Non-existing secret {scope}:{key} was attempted to be removed.")
                return

        self._peer_data(scope)[key] = value

    def set_secret(self, scope: secrets.Scopes, key: str, value: typing.Optional[str]) -> None:
        """Set a secret in the secret storage."""
        if scope not in [secrets.APP_SCOPE, secrets.UNIT_SCOPE]:
            raise MySQLRouterSecretsError(f"Invalid secret scope: {scope}")

        if scope == secrets.APP_SCOPE and not self.unit.is_leader():
            raise MySQLRouterSecretsError("Can only set app secrets on the leader unit")

        if ops.jujuversion.JujuVersion.from_environ().has_secrets:
            self._set_secret_in_juju(scope, key, value)

            # for refresh from juju <= 3.1.4 to >= 3.1.5, we need to clear out
            # secrets from the databag as well
            if self._get_secret_from_databag(scope, key):
                self._set_secret_in_databag(scope, key, None)

            return

        self._set_secret_in_databag(scope, key, value)

    # =======================
    #  Handlers
    # =======================

    def _upgrade_relation_created(self, _) -> None:
        if self._unit_lifecycle.authorized_leader:
            # `self._upgrade.is_compatible` should return `True` during first charm
            # installation/setup
            self._upgrade.set_versions_in_app_databag()

    def reconcile(self, event=None) -> None:  # noqa: C901
        """Handle most events."""
        if not self._upgrade:
            logger.debug("Peer relation not available")
            return
        if not self._upgrade.versions_set:
            logger.debug("Peer relation not ready")
            return
        workload_ = self.get_workload(event=event)
        if self._upgrade.unit_state == "restarting":  # Kubernetes only
            if not self._upgrade.is_compatible:
                logger.info(
                    "Upgrade incompatible. If you accept potential *data loss* and *downtime*, you can continue with `resume-upgrade force=true`"
                )
                self.unit.status = ops.BlockedStatus(
                    "Upgrade incompatible. Rollback to previous revision with `juju refresh`"
                )
                self.set_status(event=event, unit=False)
                return
        elif isinstance(self._upgrade, machine_upgrade.Upgrade):  # Machines only
            if not self._upgrade.is_compatible:
                self.set_status(event=event)
                return
            if self._upgrade.unit_state == "outdated":
                if self._upgrade.authorized:
                    self._upgrade.upgrade_unit(workload_=workload_, tls=False)
                else:
                    self.set_status(event=event)
                    logger.debug("Waiting to upgrade")
                    return
        logger.debug(
            "State of reconcile "
            f"{self._unit_lifecycle.authorized_leader=}, "
            f"{isinstance(workload_, workload.AuthenticatedWorkload)=}, "
            f"{workload_.container_ready=}, "
            f"{self._database_requires.is_relation_breaking(event)=}, "
            f"{self._upgrade.in_progress=}"
            f"{self._cos.is_relation_breaking(event)=}"
        )

        try:
            if self._unit_lifecycle.authorized_leader:
                if self._database_requires.is_relation_breaking(event):
                    if self._upgrade.in_progress:
                        logger.warning(
                            "Modifying relations during an upgrade is not supported. The charm may be in a broken, unrecoverable state. Re-deploy the charm"
                        )
                    self._database_provides.delete_all_databags()
                elif (
                    not self._upgrade.in_progress
                    and isinstance(workload_, workload.AuthenticatedWorkload)
                    and workload_.container_ready
                ):
                    self._database_provides.reconcile_users(
                        event=event,
                        router_read_write_endpoint=self._read_write_endpoint,
                        router_read_only_endpoint=self._read_only_endpoint,
                        shell=workload_.shell,
                    )
            if workload_.container_ready:
                cos_relation_exists = (
                    self._cos.relation_exists and not self._cos.is_relation_breaking(event)
                )
                workload_.reconcile(
                    unit_name=self.unit.name,
                    exporter_config=self._cos.exporter_user_info if cos_relation_exists else None,
                )
            # Empty waiting status means we're waiting for database requires relation before
            # starting workload
            if not workload_.status or workload_.status == ops.WaitingStatus():
                self._upgrade.unit_state = "healthy"
            if self._unit_lifecycle.authorized_leader:
                self._upgrade.reconcile_partition()
                if not self._upgrade.in_progress:
                    self._upgrade.set_versions_in_app_databag()
            self.set_status(event=event)
        except server_exceptions.Error as e:
            # If not for `unit=False`, another `server_exceptions.Error` could be thrown here
            self.set_status(event=event, unit=False)
            self.unit.status = e.status
            logger.debug(f"Set unit status to {self.unit.status}")

    def _on_resume_upgrade_action(self, event: ops.ActionEvent) -> None:
        if not self._unit_lifecycle.authorized_leader:
            message = f"Must run action on leader unit. (e.g. `juju run {self.app.name}/leader {upgrade.RESUME_ACTION_NAME}`)"
            logger.debug(f"Resume upgrade event failed: {message}")
            event.fail(message)
            return
        if not self._upgrade or not self._upgrade.in_progress:
            message = "No upgrade in progress"
            logger.debug(f"Resume upgrade event failed: {message}")
            event.fail(message)
            return
        self._upgrade.reconcile_partition(action_event=event)
