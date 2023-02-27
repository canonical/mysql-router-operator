# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from subprocess import STDOUT, CalledProcessError
from unittest.mock import patch

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


class TestMysqlRouterHelpers(unittest.TestCase):
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd")
    @patch("mysql_router_helpers.subprocess.check_output")
    def test_bootstrap_and_start_mysql_router(self, check_output, systemd, render_and_copy):
        MySQLRouter.bootstrap_and_start_mysql_router(
            "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
        )
        check_output.assert_called_with(bootstrap_cmd, stderr=STDOUT)
        render_and_copy.assert_called_with("testapp")
        systemd.daemon_reload.assert_called_with()
        systemd.service_start.assert_called_with(MYSQL_ROUTER_SERVICE_NAME)

    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd")
    @patch("mysql_router_helpers.subprocess.check_output")
    def test_bootstrap_and_start_mysql_router_force(self, check_output, systemd, render_and_copy):
        MySQLRouter.bootstrap_and_start_mysql_router(
            "test_user", "qweqwe", "testapp", "10.10.0.1", "3306", True
        )
        check_output.assert_called_with(bootstrap_cmd + ["--force"], stderr=STDOUT)
        render_and_copy.assert_called_with("testapp")
        systemd.daemon_reload.assert_called_with()
        systemd.service_start.assert_called_with(MYSQL_ROUTER_SERVICE_NAME)

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd")
    @patch("mysql_router_helpers.subprocess.check_output")
    def test_bootstrap_and_start_mysql_router_subprocess_error(
        self, check_output, systemd, render_and_copy, logger
    ):
        e = CalledProcessError(1, bootstrap_cmd)
        check_output.side_effect = e
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
            )
        check_output.assert_called_with(bootstrap_cmd, stderr=STDOUT)
        render_and_copy.assert_not_called()
        systemd.daemon_reload.assert_not_called()
        systemd.service_start.assert_not_called()
        logger.exception.assert_called_with("Failed to bootstrap mysqlrouter", exc_info=e)

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd.service_start")
    @patch("mysql_router_helpers.systemd.daemon_reload")
    @patch("mysql_router_helpers.subprocess.check_output")
    def test_bootstrap_and_start_mysql_router_systemd_error(
        self, check_output, daemon_reload, service_start, render_and_copy, logger
    ):
        e = SystemdError()
        daemon_reload.side_effect = e
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
            )
        check_output.assert_called_with(bootstrap_cmd, stderr=STDOUT)
        render_and_copy.assert_called_with("testapp")
        daemon_reload.assert_called_with()
        service_start.assert_not_called()
        logger.exception.assert_called_with(
            "Failed to set up mysqlrouter as a systemd service", exc_info=e
        )

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd.service_start")
    @patch("mysql_router_helpers.systemd.daemon_reload")
    @patch("mysql_router_helpers.subprocess.check_output")
    def test_bootstrap_and_start_mysql_router_no_daemon_reload(
        self, check_output, daemon_reload, service_start, render_and_copy, logger
    ):
        daemon_reload.return_value = False
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
            )
        check_output.assert_called_with(bootstrap_cmd, stderr=STDOUT)
        render_and_copy.assert_called_with("testapp")
        daemon_reload.assert_called_with()
        service_start.assert_not_called()
        logger.exception.assert_called_with("Failed to load the mysqlrouter systemd service")

    @patch("mysql_router_helpers.logger")
    @patch("mysql_router_helpers.MySQLRouter._render_and_copy_mysqlrouter_systemd_unit_file")
    @patch("mysql_router_helpers.systemd.service_start")
    @patch("mysql_router_helpers.systemd.daemon_reload")
    @patch("mysql_router_helpers.subprocess.check_output")
    def test_bootstrap_and_start_mysql_router_no_service_start(
        self, check_output, daemon_reload, service_start, render_and_copy, logger
    ):
        service_start.return_value = False
        with self.assertRaises(MySQLRouterBootstrapError):
            MySQLRouter.bootstrap_and_start_mysql_router(
                "test_user", "qweqwe", "testapp", "10.10.0.1", "3306"
            )
        check_output.assert_called_with(bootstrap_cmd, stderr=STDOUT)
        render_and_copy.assert_called_with("testapp")
        daemon_reload.assert_called_with()
        service_start.assert_called_with(MYSQL_ROUTER_SERVICE_NAME)
        logger.exception.assert_called_with("Failed to start the mysqlrouter systemd service")
