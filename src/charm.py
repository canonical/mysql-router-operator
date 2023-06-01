#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""MySQL Router kubernetes (k8s) charm"""

import logging
import socket

import lightkube
import lightkube.models.core_v1
import lightkube.models.meta_v1
import lightkube.resources.core_v1
import ops
import tenacity

import relations.database_provides
import relations.database_requires
import relations.tls
import workload

logger = logging.getLogger(__name__)


class MySQLRouterOperatorCharm(ops.CharmBase):
    """Operator charm for MySQL Router"""

    def __init__(self, *args) -> None:
        super().__init__(*args)

        self.database_requires = relations.database_requires.RelationEndpoint(self)

        self.database_provides = relations.database_provides.RelationEndpoint(self)

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(
            getattr(self.on, "mysql_router_pebble_ready"), self._on_mysql_router_pebble_ready
        )
        self.framework.observe(self.on.leader_elected, self._on_leader_elected)

        # Start workload after pod restart
        self.framework.observe(self.on.upgrade_charm, self.reconcile_database_relations)

        self.tls = relations.tls.RelationEndpoint(self)

    def get_workload(self, *, event):
        """MySQL Router workload"""
        container = self.unit.get_container(workload.Workload.CONTAINER_NAME)
        if connection_info := self.database_requires.get_connection_info(event=event):
            return workload.AuthenticatedWorkload(
                _container=container,
                _connection_info=connection_info,
                _charm=self,
            )
        return workload.Workload(_container=container)

    @property
    def model_service_domain(self):
        """K8s service domain for Juju model"""
        # Example: "mysql-router-k8s-0.mysql-router-k8s-endpoints.my-model.svc.cluster.local"
        fqdn = socket.getfqdn()
        # Example: "mysql-router-k8s-0.mysql-router-k8s-endpoints."
        prefix = f"{self.unit.name.replace('/', '-')}.{self.app.name}-endpoints."
        assert fqdn.startswith(f"{prefix}{self.model.name}.")
        # Example: my-model.svc.cluster.local
        return fqdn.removeprefix(prefix)

    @property
    def _endpoint(self) -> str:
        """K8s endpoint for MySQL Router"""
        # Example: mysql-router-k8s.my-model.svc.cluster.local
        return f"{self.app.name}.{self.model_service_domain}"

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

    def _patch_service(self, *, name: str, ro_port: int, rw_port: int) -> None:
        """Patch Juju-created k8s service.

        The k8s service will be tied to pod-0 so that the service is auto cleaned by
        k8s when the last pod is scaled down.

        Args:
            name: The name of the service.
            ro_port: The read only port.
            rw_port: The read write port.
        """
        logger.debug(f"Patching k8s service {name=}, {ro_port=}, {rw_port=}")
        client = lightkube.Client()
        pod0 = client.get(
            res=lightkube.resources.core_v1.Pod,
            name=self.app.name + "-0",
            namespace=self.model.name,
        )
        service = lightkube.resources.core_v1.Service(
            metadata=lightkube.models.meta_v1.ObjectMeta(
                name=name,
                namespace=self.model.name,
                ownerReferences=pod0.metadata.ownerReferences,
                labels={
                    "app.kubernetes.io/name": self.app.name,
                },
            ),
            spec=lightkube.models.core_v1.ServiceSpec(
                ports=[
                    lightkube.models.core_v1.ServicePort(
                        name="mysql-ro",
                        port=ro_port,
                        targetPort=ro_port,
                    ),
                    lightkube.models.core_v1.ServicePort(
                        name="mysql-rw",
                        port=rw_port,
                        targetPort=rw_port,
                    ),
                ],
                selector={"app.kubernetes.io/name": self.app.name},
            ),
        )
        client.patch(
            res=lightkube.resources.core_v1.Service,
            obj=service,
            name=service.metadata.name,
            namespace=service.metadata.namespace,
            force=True,
            field_manager=self.model.app.name,
        )
        logger.debug(f"Patched k8s service {name=}, {ro_port=}, {rw_port=}")

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
            f"{isinstance(event, ops.UpgradeCharmEvent)=}"
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
                router_endpoint=self._endpoint,
                shell=workload_.shell,
            )
        if isinstance(workload_, workload.AuthenticatedWorkload) and workload_.container_ready:
            if isinstance(event, ops.UpgradeCharmEvent):
                # Pod restart (https://juju.is/docs/sdk/start-event#heading--emission-sequence)
                workload_.cleanup_after_pod_restart()
            workload_.enable(tls=self.tls.certificate_saved, unit_name=self.unit.name)
        elif workload_.container_ready:
            workload_.disable()
        self.set_status(event=event)

    def _on_install(self, _) -> None:
        """Patch existing k8s service to include read-write and read-only services."""
        if not self.unit.is_leader():
            return
        try:
            self._patch_service(name=self.app.name, ro_port=6447, rw_port=6446)
        except lightkube.ApiError:
            logger.exception("Failed to patch k8s service")
            raise

    def _on_start(self, _) -> None:
        # Set status on first start if no relations active
        self.set_status(event=None)

    def _on_mysql_router_pebble_ready(self, _) -> None:
        self.unit.set_workload_version(self.get_workload(event=None).version)
        self.reconcile_database_relations()

    def _on_leader_elected(self, _) -> None:
        # Update app status
        self.set_status(event=None)


if __name__ == "__main__":
    ops.main.main(MySQLRouterOperatorCharm)
