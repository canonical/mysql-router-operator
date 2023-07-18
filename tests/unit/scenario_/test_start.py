# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import ops
import pytest
import scenario

import machine_charm


@pytest.mark.parametrize("leader", [False, True])
def test_start_sets_status_if_no_relations(leader):
    context = scenario.Context(machine_charm.MachineSubordinateRouterCharm)
    input_state = scenario.State(leader=leader)
    output_state = context.run("start", input_state)
    if leader:
        assert output_state.app_status == ops.BlockedStatus("Missing relation: backend-database")
    assert output_state.unit_status == ops.ActiveStatus()
