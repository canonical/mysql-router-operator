# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from subprocess import CalledProcessError
from unittest.mock import call, patch

from charms.operator_libs_linux.v1.systemd import SystemdError

from constants import MYSQL_ROUTER_SERVICE_NAME
from mysql_router_helpers import MySQLRouter, MySQLRouterBootstrapError

bootstrap_cmd = [
    "sudo",
    "/usr/bin/mysqlrouter",
    "--user",
    "mysql",
    "--name",
    "testapp",
    "--bootstrap",
    "test_user:qweqwe@10.10.0.1",
    "--directory",
    "/var/lib/mysql/testapp",
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
chmod_cmd = [
    "sudo",
    "chmod",
    "755",
    "/var/lib/mysql/testapp",
]


class TestMysqlRouterHelpers(unittest.TestCase):
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd")
    @patch("mysql_router_helpers.subprocess.run")
    def test_bootstrap_and_start_mysql_router(self, run, systemd, render_and_copy):
        MySQLRouter.bootstrap_and_start_mysql_router(
            "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
        )

        self.assertEqual(
            sorted(run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd),
                    call(chmod_cmd),
                ]
            ),
        )
        render_and_copy.assert_called_with("testapp")
        systemd.daemon_reload.assert_called_with()
        systemd.service_start.assert_called_with(MYSQL_ROUTER_SERVICE_NAME)

    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd")
    @patch("mysql_router_helpers.subprocess.run")
    def test_bootstrap_and_start_mysql_router_force(self, run, systemd, render_and_copy):
        MySQLRouter.bootstrap_and_start_mysql_router(
            "test_user", "qweqwe", "testapp", "10.10.0.1", "3306", force=True
        )

        self.assertEqual(
            sorted(run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd + ["--force"]),
                    call(chmod_cmd),
                ]
            ),
        )
        render_and_copy.assert_called_with("testapp")
        systemd.daemon_reload.assert_called_with()
        systemd.service_start.assert_called_with(MYSQL_ROUTER_SERVICE_NAME)

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd")
    @patch("mysql_router_helpers.subprocess.run")
    def test_bootstrap_and_start_mysql_router_subprocess_error(
        self, run, systemd, render_and_copy, logger
    ):
        e = CalledProcessError(1, bootstrap_cmd)
        run.side_effect = e
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
            )

        run.assert_called_with(bootstrap_cmd)
        render_and_copy.assert_not_called()
        systemd.daemon_reload.assert_not_called()
        systemd.service_start.assert_not_called()
        logger.exception.assert_called_with("Failed to bootstrap mysqlrouter")

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd.service_start")
    @patch("mysql_router_helpers.systemd.daemon_reload")
    @patch("mysql_router_helpers.subprocess.run")
    def test_bootstrap_and_start_mysql_router_systemd_error(
        self, run, daemon_reload, service_start, render_and_copy, logger
    ):
        e = SystemdError()
        daemon_reload.side_effect = e
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
            )

        self.assertEqual(
            sorted(run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd),
                    call(chmod_cmd),
                ]
            ),
        )
        render_and_copy.assert_called_with("testapp")
        daemon_reload.assert_called_with()
        service_start.assert_not_called()
        logger.exception.assert_called_with("Failed to set up mysqlrouter as a systemd service")

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd.service_start")
    @patch("mysql_router_helpers.systemd.daemon_reload")
    @patch("mysql_router_helpers.subprocess.run")
    def test_bootstrap_and_start_mysql_router_no_daemon_reload(
        self, run, daemon_reload, service_start, render_and_copy, logger
    ):
        daemon_reload.return_value = False
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
            )

        self.assertEqual(
            sorted(run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd),
                    call(chmod_cmd),
                ]
            ),
        )
        render_and_copy.assert_called_with("testapp")
        daemon_reload.assert_called_with()
        service_start.assert_not_called()
        logger.exception.assert_called_with("Failed to load the mysqlrouter systemd service")

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd.service_start")
    @patch("mysql_router_helpers.systemd.daemon_reload")
    @patch("mysql_router_helpers.subprocess.run")
    def test_bootstrap_and_start_mysql_router_no_service_start(
        self, run, daemon_reload, service_start, render_and_copy, logger
    ):
        service_start.return_value = False
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
            )

        self.assertEqual(
            sorted(run.mock_calls),
            sorted(
                [
                    call(bootstrap_cmd),
                    call(chmod_cmd),
                ]
            ),
        )
        render_and_copy.assert_called_with("testapp")
        daemon_reload.assert_called_with()
        service_start.assert_called_with(MYSQL_ROUTER_SERVICE_NAME)
        logger.exception.assert_called_with("Failed to start the mysqlrouter systemd service")
