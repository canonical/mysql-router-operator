#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""MySQL-Router machine charm."""

import logging
import subprocess
from typing import List

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v1 import snap
from ops.charm import CharmBase
from ops.main import main
from ops.model import BlockedStatus, MaintenanceStatus, WaitingStatus

logger = logging.getLogger(__name__)

MYSQL_SHELL = "mysql-shell"
MYSQL_ROUTER = "mysql-router"


class MySQLRouterOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)

        self.name = "mysqlrouter"
        self.framework.observe(self.on.install, self._on_install)

    def _on_install(self, _) -> None:
        """Install the packages."""
        self.unit.status = MaintenanceStatus("installing packages")

        self._install_apt_packages([MYSQL_ROUTER])
        self._install_snap_packages([MYSQL_SHELL])
        self.unit.status = WaitingStatus("waiting for database relation")

    def _install_apt_packages(self, packages: List[str]) -> None:
        """Install apt packages.

        Args:
            packages: List of apt packages to install.
        """
        try:
            logger.debug("Updating apt cache")
            apt.update()
        except subprocess.CalledProcessError as e:
            logger.exception("Failed to update apt cache", exc_info=e)
            self.unit.status = BlockedStatus("failed to install necessary packages")
            return
        for package in packages:
            try:
                apt.add_package(package)
                logger.debug(f"Installed package: {package}")
            except apt.PackageNotFoundError:
                logger.error(f"Package not found: {package}")
                self.unit.status = BlockedStatus("failed to install necessary packages")
                return
            except apt.PackageError:
                logger.error(f"Package error: {package}")
                self.unit.status = BlockedStatus("failed to install necessary packages")
                return

    def _install_snap_packages(self, packages: List[str]) -> None:
        """Install snap packages.

        Args:
            packages: List of snaps to install.
        """
        cache = snap.SnapCache()
        if not cache.snapd_installed:
            logger.warning("snapd is not installed. Installing...")
            self._install_apt_packages(["snapd"])

        for package in packages:
            try:
                snap_pack = cache[package]
                if not snap_pack.present:
                    snap_pack.ensure(snap.SnapState.Latest)
            except snap.SnapNotFoundError:
                logger.error(f"Snap not found: {package}")
                self.unit.status = BlockedStatus("failed to install necessary packages")
            except snap.SnapError as e:
                logger.error(f"Snap error: {package} with error: {e.message}")
                self.unit.status = BlockedStatus("failed to install necessary packages")


if __name__ == "__main__":
    main(MySQLRouterOperatorCharm)
