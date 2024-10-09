# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import PropertyMock

import ops
import pytest
from charms.tempo_coordinator_k8s.v0.charm_tracing import charm_tracing_disabled
from pytest_mock import MockerFixture

import snap


@pytest.fixture(autouse=True)
def disable_tenacity_retry(monkeypatch):
    for retry_class in (
        "retry_if_exception",
        "retry_if_exception_type",
        "retry_if_not_exception_type",
        "retry_unless_exception_type",
        "retry_if_exception_cause_type",
        "retry_if_result",
        "retry_if_not_result",
        "retry_if_exception_message",
        "retry_if_not_exception_message",
        "retry_any",
        "retry_all",
        "retry_always",
        "retry_never",
    ):
        monkeypatch.setattr(f"tenacity.{retry_class}.__call__", lambda *args, **kwargs: False)


@pytest.fixture(autouse=True)
def patch(monkeypatch):
    monkeypatch.setattr(
        "machine_charm.MachineSubordinateRouterCharm.wait_until_mysql_router_ready",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("workload.AuthenticatedWorkload._router_username", "")
    monkeypatch.setattr("mysql_shell.Shell._run_code", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "mysql_shell.Shell.get_mysql_router_user_for_unit", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("mysql_shell.Shell.is_router_in_cluster_set", lambda *args, **kwargs: True)
    monkeypatch.setattr("upgrade.Upgrade.in_progress", False)
    monkeypatch.setattr("upgrade.Upgrade.versions_set", True)
    monkeypatch.setattr("upgrade.Upgrade.is_compatible", True)


# flake8: noqa: C901
@pytest.fixture(autouse=True)
def machine_patch(monkeypatch):
    monkeypatch.setattr("lifecycle.Unit._on_subordinate_relation_broken", lambda *args: None)

    class Snap:
        present = False

        def __init__(self):
            self.services = {
                "mysqlrouter-service": {"active": False},
                "mysqlrouter-exporter": {"active": False},
            }

        def ensure(self, *_, **__):
            return

        def set(self, *_, **__):
            return

        def unset(self, *_, **__):
            return

        def hold(self, *_, **__):
            return

        def start(self, services: list[str] = None, *_, **__):
            for service in services:
                assert service in ("mysqlrouter-service", "mysqlrouter-exporter")

            if "mysqlrouter-service" in services:
                self.services["mysqlrouter-service"]["active"] = True
            if "mysqlrouter-exporter" in services:
                self.services["mysqlrouter-exporter"]["active"] = True

        def stop(self, services: list[str] = None, *_, **__):
            for service in services:
                assert service in ("mysqlrouter-service", "mysqlrouter-exporter")

            if "mysqlrouter-service" in services:
                self.services["mysqlrouter-service"]["active"] = False
            if "mysqlrouter-exporter" in services:
                self.services["mysqlrouter-exporter"]["active"] = False

        def restart(self, services: list[str] = []):
            if "mysqlrouter-service" in services:
                self.services["mysqlrouter-service"]["active"] = True
            if "mysqlrouter-exporter" in services:
                self.services["mysqlrouter-exporter"]["active"] = True

    monkeypatch.setattr(snap, "_snap", Snap())

    monkeypatch.setattr(
        "snap.Snap._run_command",
        lambda *args, **kwargs: "null",  # Use "null" for `json.loads()`
    )
    monkeypatch.setattr("snap._Path.read_text", lambda *args, **kwargs: "")
    monkeypatch.setattr("snap._Path.write_text", lambda *args, **kwargs: None)
    monkeypatch.setattr("snap._Path.unlink", lambda *args, **kwargs: None)
    monkeypatch.setattr("snap._Path.mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr("snap._Path.rmtree", lambda *args, **kwargs: None)

    def _network_get(*args, **kwargs) -> dict:
        """Patch for the not-yet-implemented testing backend needed for `bind_address`.

        This can be used for cases such as:
        self.model.get_binding(event.relation).network.bind_address
        Will always return '10.1.157.116'
        """
        return ops.model.Network({
            "bind-addresses": [
                {
                    "mac-address": "",
                    "interface-name": "",
                    "addresses": [{"hostname": "", "value": "10.1.157.116", "cidr": ""}],
                }
            ],
            "bind-address": "10.1.157.116",
            "egress-subnets": ["10.152.183.65/32"],
            "ingress-addresses": ["10.152.183.65"],
        })

    monkeypatch.setattr("ops.model.Binding._network_get", _network_get)


@pytest.fixture(autouse=True, params=["juju2", "juju3"])
def juju_has_secrets(mocker: MockerFixture, request):
    """This fixture will force the usage of secrets whenever run on Juju 3.x.

    NOTE: This is needed, as normally JujuVersion is set to 0.0.0 in tests
    (i.e. not the real juju version)
    """
    if request.param == "juju3":
        mocker.patch.object(
            ops.JujuVersion, "has_secrets", new_callable=PropertyMock
        ).return_value = False
        return False
    else:
        mocker.patch.object(
            ops.JujuVersion, "has_secrets", new_callable=PropertyMock
        ).return_value = True
        return True


@pytest.fixture(autouse=True)
def disable_charm_tracing():
    with charm_tracing_disabled():
        yield
