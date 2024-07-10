# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""In-place upgrades on machines

Derived from specification: DA058 - In-Place Upgrades - Kubernetes v2
(https://docs.google.com/document/d/1tLjknwHudjcHs42nzPVBNkHs98XxAOT2BXGGpP7NyEU/)
"""
import json
import logging
import time
import typing

import ops

import snap
import upgrade
import workload

if typing.TYPE_CHECKING:
    import relations.cos

logger = logging.getLogger(__name__)

FORCE_ACTION_NAME = "force-upgrade"


class Upgrade(upgrade.Upgrade):
    """In-place upgrades on machines"""

    @property
    def unit_state(self) -> typing.Optional[upgrade.UnitState]:
        if (
            self._unit_workload_container_version is not None
            and self._unit_workload_container_version != self._app_workload_container_version
        ):
            logger.debug("Unit upgrade state: outdated")
            return upgrade.UnitState.OUTDATED
        return super().unit_state

    @unit_state.setter
    def unit_state(self, value: upgrade.UnitState) -> None:
        if value is upgrade.UnitState.HEALTHY:
            # Set snap revision on first install
            self._unit_workload_container_version = snap.revision
            self._unit_workload_version = self._current_versions["workload"]
            logger.debug(
                f'Saved {snap.revision=} and {self._current_versions["workload"]=} in unit databag while setting state healthy'
            )
        # Super call
        upgrade.Upgrade.unit_state.fset(self, value)

    def _get_unit_healthy_status(
        self, *, workload_status: typing.Optional[ops.StatusBase]
    ) -> ops.StatusBase:
        if self._unit_workload_container_version == self._app_workload_container_version:
            if isinstance(workload_status, ops.WaitingStatus):
                return ops.WaitingStatus(
                    f'Router {self._unit_workload_version}; Snap rev {self._unit_workload_container_version}; Charmed operator {self._current_versions["charm"]}'
                )
            return ops.ActiveStatus(
                f'Router {self._unit_workload_version} running; Snap rev {self._unit_workload_container_version}; Charmed operator {self._current_versions["charm"]}'
            )
        if isinstance(workload_status, ops.WaitingStatus):
            return ops.WaitingStatus(
                f'Router {self._unit_workload_version}; Snap rev {self._unit_workload_container_version} (outdated); Charmed operator {self._current_versions["charm"]}'
            )
        return ops.ActiveStatus(
            f'Router {self._unit_workload_version} running; Snap rev {self._unit_workload_container_version} (outdated); Charmed operator {self._current_versions["charm"]}'
        )

    @property
    def app_status(self) -> typing.Optional[ops.StatusBase]:
        if not self.in_progress:
            return
        if not self.is_compatible:
            logger.info(
                "Upgrade incompatible. If you accept potential *data loss* and *downtime*, you can continue by running `force-upgrade` action on each remaining unit"
            )
            return ops.BlockedStatus(
                "Upgrade incompatible. Rollback to previous revision with `juju refresh`"
            )
        return super().app_status

    @property
    def _unit_workload_container_versions(self) -> typing.Dict[str, str]:
        """{Unit name: installed snap revision}"""
        versions = {}
        for unit in self._sorted_units:
            if version := (self._peer_relation.data[unit].get("snap_revision")):
                versions[unit.name] = version
        return versions

    @property
    def _unit_workload_container_version(self) -> typing.Optional[str]:
        """Installed snap revision for this unit"""
        return self._unit_databag.get("snap_revision")

    @_unit_workload_container_version.setter
    def _unit_workload_container_version(self, value: str):
        self._unit_databag["snap_revision"] = value

    @property
    def _app_workload_container_version(self) -> str:
        """Snap revision for current charm code"""
        return snap.revision

    @property
    def _unit_workload_version(self) -> typing.Optional[str]:
        """Installed MySQL Router version for this unit"""
        return self._unit_databag.get("workload_version")

    @_unit_workload_version.setter
    def _unit_workload_version(self, value: str):
        self._unit_databag["workload_version"] = value

    @property
    def authorized(self) -> bool:
        assert self._unit_workload_container_version != self._app_workload_container_version
        for index, unit in enumerate(self._sorted_units):
            if unit.name == self._unit.name:
                # Higher number units have already upgraded
                return True
            state = self._peer_relation.data[unit].get("state")
            if state:
                state = upgrade.UnitState(state)
            if (
                self._unit_workload_container_versions.get(unit.name)
                != self._app_workload_container_version
                or state is not upgrade.UnitState.HEALTHY
            ):
                # Waiting for higher number units to upgrade
                return False
        return False

    def upgrade_unit(
        self,
        *,
        event,
        workload_: workload.Workload,
        tls: bool,
        exporter_config: "relations.cos.ExporterConfig",
    ) -> None:
        logger.debug(f"Upgrading {self.authorized=}")
        self.unit_state = upgrade.UnitState.UPGRADING
        workload_.upgrade(event=event, unit=self._unit, tls=tls, exporter_config=exporter_config)
        self._unit_workload_container_version = snap.revision
        self._unit_workload_version = self._current_versions["workload"]
        logger.debug(
            f'Saved {snap.revision=} and {self._current_versions["workload"]=} in unit databag after upgrade'
        )
