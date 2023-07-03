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
import relations.database_provides
import relations.database_requires
import workload

logger = logging.getLogger(__name__)


class MySQLRouterCharm(ops.CharmBase, abc.ABC):
    """MySQL Router charm"""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        # Instantiate before registering other event observers
        self._unit_lifecycle = lifecycle.Unit(self)

        self._workload_type = workload.Workload
        self._authenticated_workload_type = workload.AuthenticatedWorkload
        self._database_requires = relations.database_requires.RelationEndpoint(self)
        self._database_provides = relations.database_provides.RelationEndpoint(self)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.leader_elected, self._on_leader_elected)

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
                connection_info=connection_info,
                charm_=self,
            )
        return self._workload_type(container_=self._container)

    @staticmethod
    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _prioritize_statuses(statuses: typing.List[ops.StatusBase]) -> ops.StatusBase:
        """Report the highest priority status.

        (Statuses of the same type are reported in the order they were added to `statuses`)
        """
        status_priority = (
            ops.BlockedStatus,
            ops.WaitingStatus,
            ops.MaintenanceStatus,
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
        statuses = []
        for endpoint in (self._database_requires, self._database_provides):
            if status := endpoint.get_status(event):
                statuses.append(status)
        return self._prioritize_statuses(statuses)

    def _determine_unit_status(self, *, event) -> ops.StatusBase:
        """Report unit status."""
        statuses = []
        if not self.get_workload(event=event).container_ready:
            statuses.append(ops.MaintenanceStatus("Waiting for container"))
        return self._prioritize_statuses(statuses)

    def set_status(self, *, event) -> None:
        """Set charm status."""
        if self._unit_lifecycle.authorized_leader:
            self.app.status = self._determine_app_status(event=event)
            logger.debug(f"Set app status to {self.app.status}")
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

    def reconcile_database_relations(self, event=None) -> None:
        """Handle database requires/provides events."""
        workload_ = self.get_workload(event=event)
        logger.debug(
            "State of reconcile "
            f"{self.unit.is_leader()=}, "
            f"{self._unit_lifecycle.authorized_leader=}, "
            f"{isinstance(workload_, workload.AuthenticatedWorkload)=}, "
            f"{workload_.container_ready=}, "
            f"{self._database_requires.is_relation_breaking(event)=}"
        )
        if self._unit_lifecycle.authorized_leader:
            if self._database_requires.is_relation_breaking(event):
                self._database_provides.delete_all_databags()
            elif (
                isinstance(workload_, workload.AuthenticatedWorkload) and workload_.container_ready
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
        self.set_status(event=event)

    def _on_start(self, _) -> None:
        # Set status on first start if no relations active
        self.set_status(event=None)

    def _on_leader_elected(self, _) -> None:
        # Update app status
        self.set_status(event=None)
