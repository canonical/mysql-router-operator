#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""MySQL Router machine charm"""

import logging

import ops

import abstract_charm
import snap
import socket_workload

logger = logging.getLogger(__name__)
# TODO VM TLS: open ports for `juju expose`


class MachineSubordinateRouterCharm(abstract_charm.MySQLRouterCharm):
    """MySQL Router machine subordinate charm"""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._workload_type = socket_workload.SocketWorkload
        self._authenticated_workload_type = socket_workload.AuthenticatedSocketWorkload
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.remove, self._on_remove)

    @property
    def _container(self) -> snap.Snap:
        return snap.Snap()

    @property
    def _read_write_endpoint(self) -> str:
        return f'file://{self._container.path("/run/mysqlrouter/mysql.sock")}'

    @property
    def _read_only_endpoint(self) -> str:
        return f'file://{self._container.path("/run/mysqlrouter/mysqlro.sock")}'

    # =======================
    #  Handlers
    # =======================

    def _on_install(self, _) -> None:
        snap.install(unit=self.unit)
        self.unit.set_workload_version(self.get_workload(event=None).version)

    def _on_remove(self, _) -> None:
        snap.uninstall()


if __name__ == "__main__":
    ops.main.main(MachineSubordinateRouterCharm)
