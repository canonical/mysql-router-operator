# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import patch

from ops.model import BlockedStatus, WaitingStatus
from ops.testing import Harness

from charm import MySQLRouterOperatorCharm
from constants import PEER
from mysql_router_helpers import MySQLRouterInstallAndConfigureError


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

    @patch("mysql_router_helpers.MySQLRouter.install_and_configure_mysql_router")
    def test_on_install(self, _install_and_configure_mysql_router):
        self.charm.on.install.emit()

        self.assertTrue(isinstance(self.harness.model.unit.status, WaitingStatus))

    @patch(
        "mysql_router_helpers.MySQLRouter.install_and_configure_mysql_router",
        side_effect=MySQLRouterInstallAndConfigureError(),
    )
    def test_on_install_exception(self, _install_and_configure_mysql_router):
        self.charm.on.install.emit()

        self.assertTrue(isinstance(self.harness.model.unit.status, BlockedStatus))
