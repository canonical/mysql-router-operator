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
import relations.cos
import relations.database_providers_wrapper
import snap
import socket_workload

logger = logging.getLogger(__name__)
# TODO VM TLS: open ports for `juju expose`


class MachineSubordinateRouterCharm(abstract_charm.MySQLRouterCharm):
    """MySQL Router machine subordinate charm"""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        # DEPRECATED shared-db: Enable legacy "mysql-shared" interface
        del self._database_provides
        self._database_provides = relations.database_providers_wrapper.RelationEndpoint(self)
        self._cos = relations.cos.COSRelation(self)

        self._authenticated_workload_type = socket_workload.AuthenticatedSocketWorkload
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.remove, self._on_remove)

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
    def _logrotate(self) -> machine_logrotate.LogRotate:
        return machine_logrotate.LogRotate(container_=self._container)

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
        snap.install(unit=self.unit, model_uuid=self.model.uuid)
        self.unit.set_workload_version(self.get_workload(event=None).version)

    def _on_remove(self, _) -> None:
        snap.uninstall()


if __name__ == "__main__":
    ops.main.main(MachineSubordinateRouterCharm)
