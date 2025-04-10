# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Router charm"""

import abc
import dataclasses
import logging
import typing

import charm_refresh
import ops

import container
import lifecycle
import logrotate
import relations.cos
import relations.database_provides
import relations.database_requires
import relations.tls
import server_exceptions
import workload

logger = logging.getLogger(__name__)


@dataclasses.dataclass(eq=False)
class RouterRefresh(charm_refresh.CharmSpecificCommon, abc.ABC):
    """MySQL Router refresh callbacks & configuration"""

    @staticmethod
    def run_pre_refresh_checks_after_1_unit_refreshed() -> None:
        pass

    @classmethod
    def is_compatible(
        cls,
        *,
        old_charm_version: charm_refresh.CharmVersion,
        new_charm_version: charm_refresh.CharmVersion,
        old_workload_version: str,
        new_workload_version: str,
    ) -> bool:
        if not super().is_compatible(
            old_charm_version=old_charm_version,
            new_charm_version=new_charm_version,
            old_workload_version=old_workload_version,
            new_workload_version=new_workload_version,
        ):
            return False
        # TODO: check workload version—prevent downgrade?
        return True


class MySQLRouterCharm(ops.CharmBase, abc.ABC):
    """MySQL Router charm"""

    _READ_WRITE_PORT = 6446
    _READ_ONLY_PORT = 6447
    _READ_WRITE_X_PORT = 6448
    _READ_ONLY_X_PORT = 6449

    refresh: charm_refresh.Common
    # Whether `reconcile` method is allowed to run
    # `False` if `charm_refresh.UnitTearingDown` or `charm_refresh.PeerRelationNotReady` raised
    # Most of the charm code should not run if either of those exceptions is raised
    # However, some charm libs (i.e. data-platform-libs) will break if they do not receive every
    # event they expect (e.g. relation-created)
    _reconcile_allowed: bool

    def __init__(self, *args) -> None:
        super().__init__(*args)
        # Instantiate before registering other event observers
        self._unit_lifecycle = lifecycle.Unit(
            self, subordinated_relation_endpoint_names=self._subordinate_relation_endpoint_names
        )

        self._workload_type = workload.Workload
        self._running_workload_type = workload.RunningWorkload
        self._database_requires = relations.database_requires.RelationEndpoint(self)
        self._database_provides = relations.database_provides.RelationEndpoint(self)
        self._cos_relation = relations.cos.COSRelation(self, self._container)
        self._ha_cluster = None
        self.tls = relations.tls.RelationEndpoint(self)

        # Observe all events (except custom events)
        for bound_event in self.on.events().values():
            if bound_event.event_type == ops.CollectStatusEvent:
                continue
            self.framework.observe(bound_event, self.reconcile)

    @property
    @abc.abstractmethod
    def _subordinate_relation_endpoint_names(self) -> typing.Optional[typing.Iterable[str]]:
        """Subordinate relation endpoint names

        Does NOT include relations where charm is principal
        """

    @property
    @abc.abstractmethod
    def _container(self) -> container.Container:
        """Workload container (snap or rock)"""

    @property
    @abc.abstractmethod
    def _logrotate(self) -> logrotate.LogRotate:
        """logrotate"""

    @property
    @abc.abstractmethod
    def _read_write_endpoints(self) -> str:
        """MySQL Router read-write endpoint"""

    @property
    @abc.abstractmethod
    def _read_only_endpoints(self) -> str:
        """MySQL Router read-only endpoint"""

    @property
    @abc.abstractmethod
    def _exposed_read_write_endpoints(self) -> typing.Optional[str]:
        """The exposed read-write endpoint.

        Only defined in vm charm.
        """

    @property
    @abc.abstractmethod
    def _exposed_read_only_endpoints(self) -> typing.Optional[str]:
        """The exposed read-only endpoint.

        Only defined in vm charm.
        """

    @abc.abstractmethod
    def is_externally_accessible(self, *, event) -> typing.Optional[bool]:
        """Whether endpoints should be externally accessible.

        Only defined in vm charm to return True/False. In k8s charm, returns None.
        """

    @property
    @abc.abstractmethod
    def _status(self) -> ops.StatusBase:
        """Status of the charm."""

    @property
    def _tls_certificate_saved(self) -> bool:
        """Whether a TLS certificate is available to use"""
        return self.tls.certificate_saved

    @property
    def _tls_key(self) -> typing.Optional[str]:
        """Custom TLS key"""
        return self.tls.key

    @property
    def _tls_certificate_authority(self) -> typing.Optional[str]:
        """Custom TLS certificate authority"""
        return self.tls.certificate_authority

    @property
    def _tls_certificate(self) -> typing.Optional[str]:
        """Custom TLS certificate"""
        return self.tls.certificate

    @property
    def tracing_endpoint(self) -> typing.Optional[str]:
        """Otlp http endpoint for charm instrumentation."""
        return self._cos_relation.tracing_endpoint

    def _cos_exporter_config(self, event) -> typing.Optional[relations.cos.ExporterConfig]:
        """Returns the exporter config for MySQLRouter exporter if cos relation exists"""
        cos_relation_exists = (
            self._cos_relation.relation_exists
            and not self._cos_relation.is_relation_breaking(event)
        )
        if cos_relation_exists:
            return self._cos_relation.exporter_user_config

    def get_workload(self, *, event, refresh: charm_refresh.Common = None):
        """MySQL Router workload

        Pass `refresh` if `self.refresh` is not set
        """
        if refresh is None:
            refresh = self.refresh
        if refresh.workload_allowed_to_start and (
            connection_info := self._database_requires.get_connection_info(event=event)
        ):
            return self._running_workload_type(
                container_=self._container,
                logrotate_=self._logrotate,
                connection_info=connection_info,
                cos=self._cos_relation,
                charm_=self,
            )
        return self._workload_type(
            container_=self._container, logrotate_=self._logrotate, cos=self._cos_relation
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
        if self.refresh.app_status_higher_priority:
            return self.refresh.app_status_higher_priority
        statuses = []
        if self._status:
            statuses.append(self._status)
        for endpoint in (self._database_requires, self._database_provides):
            if status := endpoint.get_status(event):
                statuses.append(status)
        return self._prioritize_statuses(statuses)

    def _determine_unit_status(self, *, event) -> ops.StatusBase:
        """Report unit status."""
        if self.refresh.unit_status_higher_priority:
            return self.refresh.unit_status_higher_priority
        statuses = []
        workload_ = self.get_workload(event=event)
        if status := workload_.status:
            statuses.append(status)
        # only in machine charms
        if self._ha_cluster:
            if status := self._ha_cluster.get_unit_juju_status():
                statuses.append(status)
        refresh_lower_priority = self.refresh.unit_status_lower_priority(
            workload_is_running=isinstance(workload_, workload.RunningWorkload)
        )
        if (not statuses or statuses == [ops.WaitingStatus()]) and refresh_lower_priority:
            return refresh_lower_priority
        return self._prioritize_statuses(statuses)

    def set_status(self, *, event, app=True, unit=True) -> None:
        """Set charm status."""
        if app and self._unit_lifecycle.authorized_leader:
            self.app.status = self._determine_app_status(event=event)
            logger.debug(f"Set app status to {self.app.status}")
        if unit:
            self.unit.status = self._determine_unit_status(event=event)
            logger.debug(f"Set unit status to {self.unit.status}")

    @abc.abstractmethod
    def wait_until_mysql_router_ready(self, *, event) -> None:
        """Wait until a connection to MySQL Router is possible.

        Retry every 5 seconds for up to 30 seconds.
        """

    @abc.abstractmethod
    def _reconcile_service(self) -> None:
        """Reconcile service.

        Only applies to Kubernetes charm
        """

    @abc.abstractmethod
    def _reconcile_ports(self, *, event) -> None:
        """Reconcile exposed ports.

        Only applies to Machine charm
        """

    @abc.abstractmethod
    def _update_endpoints(self) -> None:
        """Update the endpoints in the provider relation if necessary."""

    # =======================
    #  Handlers
    # =======================

    def reconcile(self, event=None) -> None:  # noqa: C901
        """Handle most events."""
        if not self._reconcile_allowed:
            logger.debug("Reconcile not allowed")
            return
        workload_ = self.get_workload(event=event)
        logger.debug(
            "State of reconcile "
            f"{self._unit_lifecycle.authorized_leader=}, "
            f"{isinstance(workload_, workload.RunningWorkload)=}, "
            f"{workload_.container_ready=}, "
            f"{self.refresh.workload_allowed_to_start=}, "
            f"{self._database_requires.is_relation_breaking(event)=}, "
            f"{self._database_requires.does_relation_exist()=}, "
            f"{self.refresh.in_progress=}, "
            f"{self._cos_relation.is_relation_breaking(event)=}"
        )
        if isinstance(self.refresh, charm_refresh.Machines):
            workload_.install(
                unit=self.unit,
                model_uuid=self.model.uuid,
                snap_revision=self.refresh.pinned_snap_revision,
                refresh=self.refresh,
            )
        self.unit.set_workload_version(workload_.version)

        # only in machine charms
        if self._ha_cluster:
            self._ha_cluster.set_vip(self.config.get("vip"))

        try:
            if self._unit_lifecycle.authorized_leader:
                if self._database_requires.is_relation_breaking(event):
                    if self.refresh.in_progress:
                        logger.warning(
                            "Modifying relations during an upgrade is not supported. The charm may be in a broken, unrecoverable state. Re-deploy the charm"
                        )
                    self._database_provides.delete_all_databags()
                elif (
                    not self.refresh.in_progress
                    and isinstance(workload_, workload.RunningWorkload)
                    and workload_.container_ready
                ):
                    self._reconcile_service()
                    self._database_provides.reconcile_users(
                        event=event,
                        router_read_write_endpoints=self._read_write_endpoints,
                        router_read_only_endpoints=self._read_only_endpoints,
                        exposed_read_write_endpoints=self._exposed_read_write_endpoints,
                        exposed_read_only_endpoints=self._exposed_read_only_endpoints,
                        shell=workload_.shell,
                    )
                    self._update_endpoints()

            if workload_.container_ready:
                workload_.reconcile(
                    event=event,
                    tls=self._tls_certificate_saved,
                    unit_name=self.unit.name,
                    exporter_config=self._cos_exporter_config(event),
                    key=self._tls_key,
                    certificate=self._tls_certificate,
                    certificate_authority=self._tls_certificate_authority,
                )
                if not self.refresh.in_progress and isinstance(
                    workload_, workload.RunningWorkload
                ):
                    self._reconcile_ports(event=event)

            logger.debug(f"{workload_.status=}")
            if not workload_.status:
                self.refresh.next_unit_allowed_to_refresh = True
            elif (
                self.refresh.workload_allowed_to_start and workload_.status == ops.WaitingStatus()
            ):
                # During scale up, this code should not be reached before the first
                # relation-created event is received on this unit since otherwise
                # `charm_refresh.PeerRelationNotReady` would be raised
                if self._database_requires.does_relation_exist():
                    # Waiting for relation-changed event before starting workload
                    pass
                else:
                    # Waiting for database requires relation; refresh can continue
                    self.refresh.next_unit_allowed_to_refresh = True
            self.set_status(event=event)
        except server_exceptions.Error as e:
            # If not for `unit=False`, another `server_exceptions.Error` could be thrown here
            self.set_status(event=event, unit=False)
            self.unit.status = e.status
            logger.debug(f"Set unit status to {self.unit.status}")
