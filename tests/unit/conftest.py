# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest


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
        "abstract_charm.MySQLRouterCharm.wait_until_mysql_router_ready",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "workload.AuthenticatedWorkload._router_username", lambda *args, **kwargs: ""
    )


@pytest.fixture(autouse=True)
def kubernetes_patch(monkeypatch):
    monkeypatch.setattr("kubernetes_charm.KubernetesRouterCharm.model_service_domain", "")
    monkeypatch.setattr(
        "rock.Rock._run_command", lambda *args, **kwargs: "null"  # Use "null" for `json.loads()`
    )
    monkeypatch.setattr("rock._Path.read_text", lambda *args, **kwargs: "")
    monkeypatch.setattr("rock._Path.write_text", lambda *args, **kwargs: None)
    monkeypatch.setattr("rock._Path.unlink", lambda *args, **kwargs: None)
    monkeypatch.setattr("rock._Path.mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr("rock._Path.rmtree", lambda *args, **kwargs: None)
