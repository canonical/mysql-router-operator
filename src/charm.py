#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""MySQL Router kubernetes (k8s) charm"""

import logging
import socket

import ops
import tenacity

import relations.database_provides
import relations.database_requires
import snap
import socket_workload
import workload

logger = logging.getLogger(__name__)


class MySQLRouterOperatorCharm(ops.CharmBase):
    """Operator charm for MySQL Router"""

    def __init__(self, *args) -> None:
        super().__init__(*args)

        self.database_requires = relations.database_requires.RelationEndpoint(self)

        self.database_provides = relations.database_provides.RelationEndpoint(self)

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.remove, self._on_remove)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.leader_elected, self._on_leader_elected)

    def get_workload(self, *, event):
        """MySQL Router workload"""
        container = snap.Snap()
        if connection_info := self.database_requires.get_connection_info(event=event):
            return socket_workload.AuthenticatedSocketWorkload(
                container_=container,
                connection_info=connection_info,
                charm_=self,
                host="",  # TODO TLS: replace with IP address when enabling TCP
            )
        return socket_workload.SocketWorkload(container_=container)

    @staticmethod
    def _prioritize_statuses(statuses: list[ops.StatusBase]) -> ops.StatusBase:
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
        for endpoint in (self.database_requires, self.database_provides):
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
        if self.unit.is_leader():
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
                stop=tenacity.stop_after_delay(30),
                wait=tenacity.wait_fixed(5),
                retry=tenacity.retry_if_exception_type(AssertionError),
                reraise=True,
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
            f"{isinstance(workload_, workload.AuthenticatedWorkload)=}, "
            f"{workload_.container_ready=}, "
            f"{self.database_requires.is_relation_breaking(event)=}, "
        )
        if self.unit.is_leader() and self.database_requires.is_relation_breaking(event):
            self.database_provides.delete_all_databags()
        elif (
            self.unit.is_leader()
            and isinstance(workload_, workload.AuthenticatedWorkload)
            and workload_.container_ready
        ):
            self.database_provides.reconcile_users(
                event=event,
                router_read_write_endpoint=workload_.read_write_endpoint,
                router_read_only_endpoint=workload_.read_only_endpoint,
                shell=workload_.shell,
            )
        if isinstance(workload_, workload.AuthenticatedWorkload) and workload_.container_ready:
            workload_.enable(
                unit_name=self.unit.name,
                tls=False,  # TODO TLS
            )
        elif workload_.container_ready:
            workload_.disable()
        self.set_status(event=event)

    def _on_install(self, _) -> None:
        snap.Installer().install(unit=self.unit)
        workload_ = self.get_workload(event=None)
        if workload_.container_ready:  # check for VM instead?
            self.unit.set_workload_version(workload_.version)

    def _on_remove(self, _) -> None:
        snap.Installer().uninstall()

    def _on_start(self, _) -> None:
        # Set status on first start if no relations active
        self.set_status(event=None)

    def _on_leader_elected(self, _) -> None:
        # Update app status
        self.set_status(event=None)


if __name__ == "__main__":
    ops.main.main(MySQLRouterOperatorCharm)
