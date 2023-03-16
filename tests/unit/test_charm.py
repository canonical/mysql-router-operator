# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from unittest.mock import patch

from ops.model import ActiveStatus, BlockedStatus, WaitingStatus
from ops.testing import Harness

from charm import MySQLRouterOperatorCharm
from constants import MYSQL_ROUTER_REQUIRES_DATA, PEER
from mysql_router_helpers import (
    MySQLRouterBootstrapError,
    MySQLRouterInstallAndConfigureError,
)


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(MySQLRouterOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.peer_relation_id = self.harness.add_relation(f"{PEER}", f"{PEER}")
        self.harness.begin()
        self.charm = self.harness.charm

    def test_get_secret(self):
        self.harness.set_leader()

        # Test application scope
        self.assertIsNone(self.charm._get_secret("app", "password"))
        self.harness.update_relation_data(
            self.peer_relation_id, self.charm.app.name, {"password": "test-password"}
        )
        self.assertEqual(self.charm._get_secret("app", "password"), "test-password")

        # Test unit scope
        self.assertIsNone(self.charm._get_secret("unit", "password"))
        self.harness.update_relation_data(
            self.peer_relation_id, self.charm.unit.name, {"password": "test-password"}
        )
        self.assertEqual(self.charm._get_secret("unit", "password"), "test-password")

    def test_set_secret(self):
        self.harness.set_leader()

        # Test application scope
        self.assertNotIn(
            "password", self.harness.get_relation_data(self.peer_relation_id, self.charm.app.name)
        )
        self.charm._set_secret("app", "password", "test-password")
        self.assertEqual(
            self.harness.get_relation_data(self.peer_relation_id, self.charm.app.name)["password"],
            "test-password",
        )

        # Test unit scope
        self.assertNotIn(
            "password", self.harness.get_relation_data(self.peer_relation_id, self.charm.unit.name)
        )
        self.charm._set_secret("unit", "password", "test-password")
        self.assertEqual(
            self.harness.get_relation_data(self.peer_relation_id, self.charm.unit.name)[
                "password"
            ],
            "test-password",
        )

    @patch("subprocess.check_call")
    @patch("mysql_router_helpers.MySQLRouter.install_and_configure_mysql_router")
    def test_on_install(self, _install_and_configure_mysql_router, _check_call):
        self.charm.on.install.emit()

        self.assertTrue(isinstance(self.harness.model.unit.status, WaitingStatus))

    @patch(
        "mysql_router_helpers.MySQLRouter.install_and_configure_mysql_router",
        side_effect=MySQLRouterInstallAndConfigureError(),
    )
    def test_on_install_exception(self, _install_and_configure_mysql_router):
        self.charm.on.install.emit()

        self.assertTrue(isinstance(self.harness.model.unit.status, BlockedStatus))

    @patch("charm.DatabaseProvidesRelation._get_related_app_name")
    @patch("charm.MySQLRouterOperatorCharm._get_secret")
    @patch("mysql_router_helpers.MySQLRouter.bootstrap_and_start_mysql_router")
    def test_on_upgrade_charm(
        self, bootstrap_and_start_mysql_router, get_secret, get_related_app_name
    ):
        self.charm.unit.status = ActiveStatus()
        get_secret.return_value = "s3kr1t"
        get_related_app_name.return_value = "testapp"
        self.charm.app_peer_data[MYSQL_ROUTER_REQUIRES_DATA] = json.dumps(
            {
                "username": "test_user",
                "endpoints": "10.10.0.1:3306,10.10.0.2:3306",
            }
        )
        self.charm.on.upgrade_charm.emit()

        self.assertTrue(isinstance(self.harness.model.unit.status, ActiveStatus))
        bootstrap_and_start_mysql_router.assert_called_with(
            "test_user", "s3kr1t", "testapp", "10.10.0.1", "3306", force=True
        )

    @patch("mysql_router_helpers.MySQLRouter.bootstrap_and_start_mysql_router")
    def test_on_upgrade_charm_waiting(self, bootstrap_and_start_mysql_router):
        self.charm.unit.status = WaitingStatus()
        self.charm.on.upgrade_charm.emit()

        self.assertTrue(isinstance(self.harness.model.unit.status, WaitingStatus))
        bootstrap_and_start_mysql_router.assert_not_called()

    @patch("charm.DatabaseProvidesRelation._get_related_app_name")
    @patch("charm.MySQLRouterOperatorCharm._get_secret")
    @patch("mysql_router_helpers.MySQLRouter.bootstrap_and_start_mysql_router")
    def test_on_upgrade_charm_error(
        self, bootstrap_and_start_mysql_router, get_secret, get_related_app_name
    ):
        bootstrap_and_start_mysql_router.side_effect = MySQLRouterBootstrapError()
        get_secret.return_value = "s3kr1t"
        get_related_app_name.return_value = "testapp"
        self.charm.unit.status = ActiveStatus()
        self.charm.app_peer_data[MYSQL_ROUTER_REQUIRES_DATA] = json.dumps(
            {
                "username": "test_user",
                "endpoints": "10.10.0.1:3306,10.10.0.2:3306",
            }
        )
        self.charm.on.upgrade_charm.emit()

        self.assertTrue(isinstance(self.harness.model.unit.status, BlockedStatus))
        bootstrap_and_start_mysql_router.assert_called_with(
            "test_user", "s3kr1t", "testapp", "10.10.0.1", "3306", force=True
        )
