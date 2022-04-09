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

        self.assertTrue(isinstance(self.harness.charm.unit.status, WaitingStatus))

    @patch("charms.operator_libs_linux.v0.apt.add_package")
    @patch("charms.operator_libs_linux.v0.apt.update")
    def test_install_apt_packages(self, _update, _add_package):
        """Test the _install_apt_packages method.

        Tests upstream package not found.
        Tests package installed (happy path)
        Tests on apt-get update fail.
        """
        # Test with a not found package.
        _add_package.side_effect = apt.PackageNotFoundError
        self.harness.charm._install_apt_packages(["mysql-router"])
        _update.assert_called_once()
        _add_package.assert_called_once_with("mysql-router")
        self.assertTrue(isinstance(self.harness.model.unit.status, BlockedStatus))

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

        # On error, assert exception is raised.
        self.harness.charm._install_apt_packages(["mysql-router"])
        _update.assert_called_once()
        self.assertTrue(isinstance(self.harness.model.unit.status, BlockedStatus))

    @patch("charms.operator_libs_linux.v1.snap.SnapCache")
    def test_install_snap_packages(self, _snap_cache):
        """Test the _install_snap_packages method.

        Tests when snap package is not found.
        Tests package installed (happy path).
        """
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

        self.harness.charm._install_snap_packages(["mysql-shell"])

        self.assertTrue(isinstance(self.harness.model.unit.status, BlockedStatus))

        # Then test a valid package.
        _snap_cache.reset_mock()
        mock_ensure.reset_mock()
        mock_ensure.side_effect = None
        self.harness.charm._install_snap_packages(["mysql-shell"])
        # Assert ensure (installing method) is called.
        mock_ensure.assert_called_once()
        # Assert the snap cache is called.
        _snap_cache.assert_called_once()
