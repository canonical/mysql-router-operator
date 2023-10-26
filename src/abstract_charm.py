# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Router charm"""

import abc
import logging
import socket
import typing

import ops
import tenacity

import container
import lifecycle
import logrotate
import machine_upgrade
import relations.database_provides
import relations.database_requires
import upgrade
import workload

logger = logging.getLogger(__name__)


class MySQLRouterCharm(ops.CharmBase, abc.ABC):
    """MySQL Router charm"""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        # Instantiate before registering other event observers
        self._unit_lifecycle = lifecycle.Unit(
            self, subordinated_relation_endpoint_names=self._subordinate_relation_endpoint_names
        )

        self._workload_type = workload.Workload
        self._authenticated_workload_type = workload.AuthenticatedWorkload
        self._database_requires = relations.database_requires.RelationEndpoint(self)
        self._database_provides = relations.database_provides.RelationEndpoint(self)
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
    def _tls_certificate_saved(self) -> bool:
        """Whether a TLS certificate is available to use"""
        # TODO VM TLS: Remove property after implementing TLS on machine charm
        return False

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

    def get_workload(self, *, event):
        """MySQL Router workload"""
        if connection_info := self._database_requires.get_connection_info(event=event):
            return self._authenticated_workload_type(
                container_=self._container,
                logrotate_=self._logrotate,
                connection_info=connection_info,
                charm_=self,
            )
        return self._workload_type(container_=self._container, logrotate_=self._logrotate)

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
        self.unit.status = ops.WaitingStatus("MySQL Router starting")
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
                    self._upgrade.upgrade_unit(
                        workload_=workload_, tls=self._tls_certificate_saved
                    )
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
        )
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
        if isinstance(workload_, workload.AuthenticatedWorkload) and workload_.container_ready:
            workload_.enable(tls=self._tls_certificate_saved, unit_name=self.unit.name)
        elif workload_.container_ready:
            workload_.disable()
        # Empty waiting status means we're waiting for database requires relation before starting
        # workload
        if not workload_.status or workload_.status == ops.WaitingStatus():
            self._upgrade.unit_state = "healthy"
        if self._unit_lifecycle.authorized_leader:
            self._upgrade.reconcile_partition()
            if not self._upgrade.in_progress:
                self._upgrade.set_versions_in_app_databag()
        self.set_status(event=event)

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
