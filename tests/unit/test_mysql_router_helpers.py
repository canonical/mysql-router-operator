# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from subprocess import CalledProcessError
from unittest.mock import MagicMock, call, patch

from charms.operator_libs_linux.v1 import snap

from constants import CHARMED_MYSQL_ROUTER_SERVICE, CHARMED_MYSQL_SNAP
from mysql_router_helpers import MySQLRouter, MySQLRouterBootstrapError

bootstrap_cmd = [
    "sudo",
    "charmed-mysql.mysqlrouter",
    "--user",
    "snap_daemon",
    "--bootstrap",
    "test_user:qweqwe@10.10.0.1",
    "--conf-use-sockets",
    "--conf-bind-address",
    "127.0.0.1",
    "--conf-base-port",
    "3306",
    "--conf-set-option",
    "DEFAULT.server_ssl_mode=PREFERRED",
    "--conf-set-option",
    "http_server.bind_address=127.0.0.1",
    "--conf-use-gr-notifications",
]
replace_socket_location_cmd = [
    "sudo",
    "sed",
    "-Ei",
    "s:/tmp/(.+).sock:/var/snap/charmed-mysql/common/var/run/mysqlrouter/\\1.sock:g",
    "/var/snap/charmed-mysql/current/etc/mysqlrouter/mysqlrouter.conf",
]


class TestMysqlRouterHelpers(unittest.TestCase):
    @patch("mysql_router_helpers.subprocess.run")
    @patch("mysql_router_helpers.snap.SnapCache")
    def test_bootstrap_and_start_mysql_router(self, _snap_cache, _run):
        _charmed_mysql_mock = MagicMock()
        _cache = {CHARMED_MYSQL_SNAP: _charmed_mysql_mock}
        _snap_cache.return_value.__getitem__.side_effect = _cache.__getitem__

        MySQLRouter.bootstrap_and_start_mysql_router("test_user", "qweqwe", "10.10.0.1", "3306")

        self.assertEqual(
            sorted(_run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd, check=True),
                    call(replace_socket_location_cmd, check=True),
                ]
            ),
        )
        _charmed_mysql_mock.start.assert_called_once()

    @patch("mysql_router_helpers.subprocess.run")
    @patch("mysql_router_helpers.snap.SnapCache")
    def test_bootstrap_and_start_mysql_router_force(self, _snap_cache, _run):
        _charmed_mysql_mock = MagicMock()
        _cache = {CHARMED_MYSQL_SNAP: _charmed_mysql_mock}
        _snap_cache.return_value.__getitem__.side_effect = _cache.__getitem__

        MySQLRouter.bootstrap_and_start_mysql_router(
            "test_user", "qweqwe", "10.10.0.1", "3306", force=True
        )

        self.assertEqual(
            sorted(_run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd + ["--force"], check=True),
                    call(replace_socket_location_cmd, check=True),
                ]
            ),
        )
        _charmed_mysql_mock.start.assert_called_once()

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.subprocess.run")
    @patch("mysql_router_helpers.snap.SnapCache")
    def test_bootstrap_and_start_mysql_router_subprocess_error(self, _snap_cache, _run, _logger):
        e = CalledProcessError(1, bootstrap_cmd)
        _run.side_effect = e
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "10.10.0.1", "3306"
            )

        _run.assert_called_once_with(bootstrap_cmd, check=True)
        _logger.exception.assert_called_with("Failed to bootstrap and start mysqlrouter")

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.subprocess.run")
    @patch("mysql_router_helpers.snap.SnapCache")
    def test_bootstrap_and_start_mysql_router_snap_error(self, _snap_cache, _run, _logger):
        e = snap.SnapError()
        _snap_cache.return_value.__getitem__.side_effect = e
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "10.10.0.1", "3306"
            )

        self.assertEqual(
            sorted(_run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd, check=True),
                    call(replace_socket_location_cmd, check=True),
                ]
            ),
        )
        _logger.exception.assert_called_with(
            f"Failed to start snap service {CHARMED_MYSQL_ROUTER_SERVICE}"
        )

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.subprocess.run")
    @patch("mysql_router_helpers.snap.SnapCache")
    def test_bootstrap_and_start_mysql_router_no_service_start(self, _snap_cache, _run, _logger):
        _charmed_mysql_mock = MagicMock()
        _cache = {CHARMED_MYSQL_SNAP: _charmed_mysql_mock}
        _snap_cache.return_value.__getitem__.side_effect = _cache.__getitem__

        _services = {CHARMED_MYSQL_ROUTER_SERVICE: {"active": False}}
        _charmed_mysql_mock.services.__getitem__.side_effect = _services.__getitem__

        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "10.10.0.1", "3306"
            )

        self.assertEqual(
            sorted(_run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd, check=True),
                    call(replace_socket_location_cmd, check=True),
                ]
            ),
        )
        _logger.exception.assert_called_with("Failed to start the mysqlrouter snap service")
