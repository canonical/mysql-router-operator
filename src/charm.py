#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""MySQL Router machine charm"""

import ops

from architecture import WrongArchitectureWarningCharm, is_wrong_architecture

if is_wrong_architecture() and __name__ == "__main__":
    ops.main.main(WrongArchitectureWarningCharm)

import dataclasses
import logging
import socket
import typing

import charm_refresh
import ops.log
import tenacity
from charms.tempo_coordinator_k8s.v0.charm_tracing import trace_charm

import abstract_charm
import logrotate
import machine_logrotate
import machine_workload
import relations.database_providers_wrapper
import relations.hacluster
import snap
import workload

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@dataclasses.dataclass(eq=False)
class _MachinesRouterRefresh(abstract_charm.RouterRefresh, charm_refresh.CharmSpecificMachines):
    _charm: abstract_charm.MySQLRouterCharm

    def refresh_snap(
        self, *, snap_name: str, snap_revision: str, refresh: charm_refresh.Machines
    ) -> None:
        # TODO: issue on relation-broken event since event not passed? mitigated by regular event handler?
        self._charm.get_workload(event=None, refresh=refresh).refresh(
            event=None,
            unit=self._charm.unit,
            model_uuid=self._charm.model.uuid,
            snap_revision=snap_revision,
            refresh=refresh,
            tls=self._charm._tls_certificate_saved,
            exporter_config=self._charm._cos_exporter_config(event=None),
        )
        # `reconcile()` will run on every event, which will set
        # `refresh.next_unit_allowed_to_refresh = True`
        # (This method will run in the charm's __init__, before `reconcile()` is called by ops)


@trace_charm(
    tracing_endpoint="tracing_endpoint",
    extra_types=(
        logrotate.LogRotate,
        machine_workload.RunningMachineWorkload,
        relations.cos.COSRelation,
        relations.database_providers_wrapper.RelationEndpoint,
        relations.database_requires.RelationEndpoint,
        relations.tls.RelationEndpoint,
        snap.Snap,
        workload.Workload,
    ),
)
class MachineSubordinateRouterCharm(abstract_charm.MySQLRouterCharm):
    """MySQL Router machine subordinate charm"""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        # Show logger name (module name) in logs
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, ops.log.JujuLogHandler):
                handler.setFormatter(logging.Formatter("{name}:{message}", style="{"))

        # DEPRECATED shared-db: Enable legacy "mysql-shared" interface
        self._database_provides = relations.database_providers_wrapper.RelationEndpoint(
            self, self._database_provides
        )
        self._running_workload_type = machine_workload.RunningMachineWorkload
        self._ha_cluster = relations.hacluster.HACluster(self)
        try:
            self.refresh = charm_refresh.Machines(
                _MachinesRouterRefresh(
                    workload_name="Router", charm_name="mysql-router", _charm=self
                )
            )
        except charm_refresh.UnitTearingDown:
            # MySQL server charm will clean up users & router metadata when the MySQL Router app or
            # unit(s) tear down
            self.unit.status = ops.MaintenanceStatus("Tearing down")
            snap.uninstall()
            self._reconcile_allowed = False
        except charm_refresh.PeerRelationNotReady:
            self.unit.status = ops.MaintenanceStatus("Waiting for peer relation")
            if self.unit.is_leader():
                self.app.status = ops.MaintenanceStatus("Waiting for peer relation")
            self._reconcile_allowed = False
        else:
            self._reconcile_allowed = True

    @property
    def _subordinate_relation_endpoint_names(self) -> typing.Optional[typing.Iterable[str]]:
        return (
            "database",
            "shared-db",  # DEPRECATED shared-db
        )

    @property
    def _container(self) -> snap.Snap:
        return snap.Snap(unit_name=self.unit.name)

    def _status(self, *, event) -> typing.Optional[ops.StatusBase]:
        pass

    @property
    def _logrotate(self) -> machine_logrotate.LogRotate:
        return machine_logrotate.LogRotate(container_=self._container)

    @property
    def host_address(self) -> str:
        """The host address for the machine."""
        if (
            not self.is_externally_accessible(event=None)
            or not self.config.get("vip")
            or (self._ha_cluster and not self._ha_cluster.is_clustered())
        ):
            return str(self.model.get_binding("juju-info").network.bind_address)

        return self.config["vip"]

    def _read_write_endpoints(self, *, event) -> str:
        if self.is_externally_accessible(event=event):
            return f"{self.host_address}:{self._READ_WRITE_PORT}"
        else:
            return f"file://{self._container.path('/run/mysqlrouter/mysql.sock')}"

    def _read_only_endpoints(self, *, event) -> str:
        if self.is_externally_accessible(event=event):
            return f"{self.host_address}:{self._READ_ONLY_PORT}"
        else:
            return f"file://{self._container.path('/run/mysqlrouter/mysqlro.sock')}"

    def is_externally_accessible(self, *, event) -> typing.Optional[bool]:
        return self._database_provides.external_connectivity(event)

    def _reconcile_service(self) -> None:
        """Only applies to Kubernetes charm, so no-op."""
        pass

    def _reconcile_ports(self, *, event) -> None:
        if self.is_externally_accessible(event=event):
            ports = [self._READ_WRITE_PORT, self._READ_ONLY_PORT]
        else:
            ports = []
        self.unit.set_ports(*ports)

    def _update_endpoints(self, *, event) -> None:
        self._database_provides.update_endpoints(
            router_read_write_endpoints=self._read_write_endpoints(event=event),
            router_read_only_endpoints=self._read_only_endpoints(event=event),
        )

    def _wait_until_service_reconciled(self) -> None:
        """Only applies to Kubernetes charm, so no-op."""
        pass

    def wait_until_mysql_router_ready(self, *, event) -> None:
        logger.debug("Waiting until MySQL Router is ready")
        self.unit.status = ops.MaintenanceStatus("MySQL Router starting")
        try:
            for attempt in tenacity.Retrying(
                reraise=True,
                stop=tenacity.stop_after_delay(30),
                wait=tenacity.wait_fixed(5),
            ):
                with attempt:
                    if self.is_externally_accessible(event=event):
                        for port in (
                            self._READ_WRITE_PORT,
                            self._READ_ONLY_PORT,
                            self._READ_WRITE_X_PORT,
                            self._READ_ONLY_X_PORT,
                        ):
                            with socket.socket() as s:
                                assert s.connect_ex(("localhost", port)) == 0
                    else:
                        for socket_file in (
                            "/run/mysqlrouter/mysql.sock",
                            "/run/mysqlrouter/mysqlro.sock",
                        ):
                            assert self._container.path(socket_file).exists()
                            with socket.socket(socket.AF_UNIX) as s:
                                assert s.connect_ex(str(self._container.path(socket_file))) == 0
        except AssertionError:
            logger.exception("Unable to connect to MySQL Router")
            raise
        else:
            logger.debug("MySQL Router is ready")


if __name__ == "__main__":
    ops.main.main(MachineSubordinateRouterCharm)
