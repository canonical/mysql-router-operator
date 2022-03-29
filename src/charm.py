#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
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
        """Install apt packages."""
        try:
            logger.debug("Updating apt cache")
            apt.update()
        except subprocess.CalledProcessError as e:
            logger.exception("Failed to update apt cache", exc_info=e)
            self.unit.status = BlockedStatus("failed to update apt cache")
            raise e
        for package in packages:
            try:
                apt.add_package(package)
                logger.debug(f"Installed package: {package}")
            except apt.PackageNotFoundError as e:
                logger.error(f"Package not found: {package}")
                self.unit.status = BlockedStatus(f"package not found: {package}")
                raise e
            except apt.PackageError as e:
                logger.error(f"Package error: {package}")
                self.unit.status = BlockedStatus(f"package error: {package}")
                raise e

    def _install_snap_packages(self, packages: List[str]) -> None:
        """Install snap packages."""
        cache = snap.SnapCache()
        if not cache.snapd_installed:
            logger.warning("snapd is not installed. Installing...")
            self._install_apt_packages(["snapd"])

        for package in packages:
            try:
                pack = cache[package]
                if not pack.present:
                    snap.add(pack.name)
            except snap.SnapNotFoundError as e:
                logger.error(f"Snap not found: {package}")
                self.unit.status = BlockedStatus(f"snap not found: {package}")
                raise e
            except snap.SnapError as e:
                logger.error(f"Snap error: {package} with error: {e.message}")
                self.unit.status = BlockedStatus(f"snap error: {package}")
                raise e


if __name__ == "__main__":
    main(MySQLRouterOperatorCharm)
