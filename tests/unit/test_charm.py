# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v1 import snap
from ops.model import BlockedStatus, WaitingStatus
from ops.testing import Harness

from charm import MySQLRouterOperatorCharm


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(MySQLRouterOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.maxDiff = None
        self.name = "mysqlrouter"

    @patch("charm.MySQLRouterOperatorCharm._install_apt_packages")
    @patch("charm.MySQLRouterOperatorCharm._install_snap_packages")
    def test_on_install(self, _install_snap_packages, _install_apt_packages):
        """Test the on_install method."""
        self.harness.charm.on.install.emit()
        _install_apt_packages.assert_called_once()
        _install_snap_packages.assert_called_once()

        self.assertEqual(
            self.harness.charm.unit.status, WaitingStatus("waiting for database relation")
        )

    @patch("charms.operator_libs_linux.v0.apt.add_package")
    @patch("charms.operator_libs_linux.v0.apt.update")
    def test_install_apt_packages(self, _update, _add_package):
        """Test the _install_apt_packages method."""
        # Test with a not found package.
        _add_package.side_effect = apt.PackageNotFoundError
        with self.assertRaises(apt.PackageNotFoundError):
            self.harness.charm._install_apt_packages(["mysql-router"])
        _update.assert_called_once()
        _add_package.assert_called_once_with("mysql-router")
        self.assertEqual(
            self.harness.model.unit.status,
            BlockedStatus("package not found: mysql-router"),
        )

        # Test a valid package.
        _update.reset_mock()
        _add_package.reset_mock()
        _add_package.side_effect = None
        self.harness.charm._install_apt_packages(["mysql-router"])
        _update.assert_called_once()
        _add_package.assert_called_once_with("mysql-router")

        # Test apt error
        _update.reset_mock()
        _update.side_effect = subprocess.CalledProcessError(returncode=127, cmd="apt-get update")

        with self.assertRaises(subprocess.CalledProcessError):
            self.harness.charm._install_apt_packages(["mysql-router"])
        _update.assert_called_once()
        self.assertEqual(
            self.harness.model.unit.status, BlockedStatus("failed to update apt cache")
        )

    @patch("charms.operator_libs_linux.v1.snap.SnapCache")
    def test_install_snap_packages(self, _snap_cache):
        """Test the _install_snap_packages method."""
        # Test with a not found package.
        mock_cache = MagicMock()
        mock_cache.snapd_installed = True
        _snap_cache.return_value = mock_cache

        mock_mysql_shell = MagicMock()
        mock_cache.__getitem__.return_value = mock_mysql_shell
        mock_mysql_shell.present = False

        mock_ensure = MagicMock()
        mock_mysql_shell.ensure = mock_ensure
        mock_ensure.side_effect = snap.SnapNotFoundError

        with self.assertRaises(snap.SnapNotFoundError):
            self.harness.charm._install_snap_packages(["mysql-shell"])
        self.assertEqual(
            self.harness.model.unit.status,
            BlockedStatus("snap not found: mysql-shell"),
        )

        # Then test a valid package.
        _snap_cache.reset_mock()
        mock_ensure.reset_mock()
        mock_ensure.side_effect = None

        self.harness.charm._install_snap_packages(["mysql-shell"])
        mock_ensure.assert_called_once()
        _snap_cache.assert_called_once()
