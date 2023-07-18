# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import ops
import pytest
import scenario

import kubernetes_charm


@pytest.mark.parametrize(
    "can_connect,unit_status",
    [(False, ops.MaintenanceStatus("Waiting for container")), (True, ops.ActiveStatus())],
)
@pytest.mark.parametrize("leader", [False, True])
def test_start_sets_status_if_no_relations(leader, can_connect, unit_status):
    context = scenario.Context(kubernetes_charm.KubernetesRouterCharm)
    input_state = scenario.State(
        containers=[scenario.Container("mysql-router", can_connect=can_connect)], leader=leader
    )
    output_state = context.run("start", input_state)
    if leader:
        assert output_state.app_status == ops.BlockedStatus("Missing relation: backend-database")
    assert output_state.unit_status == unit_status
