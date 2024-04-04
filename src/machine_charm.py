#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""MySQL Router machine charm"""

import logging
import typing

import ops

import abstract_charm
import machine_logrotate
import machine_upgrade
import relations.database_providers_wrapper
import snap
import socket_workload
import upgrade

logger = logging.getLogger(__name__)
# TODO VM TLS: open ports for `juju expose`


class MachineSubordinateRouterCharm(abstract_charm.MySQLRouterCharm):
    """MySQL Router machine subordinate charm"""

    READ_WRITE_PORT = 6446
    READ_ONLY_PORT = 6447

    def __init__(self, *args) -> None:
        super().__init__(*args)
        # DEPRECATED shared-db: Enable legacy "mysql-shared" interface
        self._database_provides = relations.database_providers_wrapper.RelationEndpoint(
            self, self._database_provides
        )
        self._authenticated_workload_type = socket_workload.AuthenticatedSocketWorkload
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.remove, self._on_remove)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on["force-upgrade"].action, self._on_force_upgrade_action)

    @property
    def _subordinate_relation_endpoint_names(self) -> typing.Optional[typing.Iterable[str]]:
        return (
            "database",
            "shared-db",  # DEPRECATED shared-db
        )

    @property
    def _container(self) -> snap.Snap:
        return snap.Snap()

    @property
    def _upgrade(self) -> typing.Optional[machine_upgrade.Upgrade]:
        try:
            return machine_upgrade.Upgrade(self)
        except upgrade.PeerRelationNotReady:
            pass

    @property
    def _logrotate(self) -> machine_logrotate.LogRotate:
        return machine_logrotate.LogRotate(container_=self._container)

    @property
    def _host_address(self) -> str:
        """The host address for the machine."""
        return self.model.get_binding(upgrade.PEER_RELATION_ENDPOINT_NAME).network.bind_address

    @property
    def _read_write_endpoint(self) -> str:
        if self._database_provides.is_exposed:
            return f"{self._host_address}:{self.READ_WRITE_PORT}"
        return f'file://{self._container.path("/run/mysqlrouter/mysql.sock")}'

    @property
    def _read_only_endpoint(self) -> str:
        if self._database_provides.is_exposed:
            return f"{self._host_address}:{self.READ_ONLY_PORT}"
        return f'file://{self._container.path("/run/mysqlrouter/mysqlro.sock")}'

    # =======================
    #  Handlers
    # =======================

    def _on_install(self, _) -> None:
        snap.install(unit=self.unit, model_uuid=self.model.uuid)
        self.unit.set_workload_version(self.get_workload(event=None).version)

    def _on_remove(self, _) -> None:
        snap.uninstall()

    def _on_upgrade_charm(self, _) -> None:
        if self._unit_lifecycle.authorized_leader:
            if not self._upgrade.in_progress:
                logger.info("Charm upgraded. MySQL Router version unchanged")
            self._upgrade.upgrade_resumed = False
            # Only call `reconcile` on leader unit to avoid race conditions with `upgrade_resumed`
            self.reconcile()

    def _on_force_upgrade_action(self, event: ops.ActionEvent) -> None:
        if not self._upgrade or not self._upgrade.in_progress:
            message = "No upgrade in progress"
            logger.debug(f"Force upgrade event failed: {message}")
            event.fail(message)
            return
        if not self._upgrade.upgrade_resumed:
            message = f"Run `juju run {self.app.name}/leader resume-upgrade` before trying to force upgrade"
            logger.debug(f"Force upgrade event failed: {message}")
            event.fail(message)
            return
        if self._upgrade.unit_state != "outdated":
            message = "Unit already upgraded"
            logger.debug(f"Force upgrade event failed: {message}")
            event.fail(message)
            return
        logger.debug("Forcing upgrade")
        event.log(f"Forcefully upgrading {self.unit.name}")
        self._upgrade.upgrade_unit(
            workload_=self.get_workload(event=None), tls=self._tls_certificate_saved
        )
        self.reconcile()
        event.set_results({"result": f"Forcefully upgraded {self.unit.name}"})
        logger.debug("Forced upgrade")

    def reconcile(self, event=None) -> None:
        self._database_provides.reconcile_ports()
        super().reconcile(event=event)


if __name__ == "__main__":
    ops.main.main(MachineSubordinateRouterCharm)
