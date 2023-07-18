# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test app status and relation databags"""

import ops
import pytest
import scenario

import kubernetes_charm

from ..wrapper import Relation
from . import combinations


def output_state(
    *, relations: list[Relation | scenario.Relation], event: scenario.Event
) -> scenario.State:
    for index, relation in enumerate(relations):
        if isinstance(relation, Relation):
            relations[index] = relation.freeze()
    relations: list[scenario.Relation]
    context = scenario.Context(kubernetes_charm.KubernetesRouterCharm)
    container = scenario.Container("mysql-router", can_connect=True)
    input_state = scenario.State(
        relations=relations,
        containers=[container],
        leader=True,
    )
    return context.run(event, input_state)


@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
def test_breaking_requires_and_complete_provides(complete_requires, complete_provides_s):
    for provides in complete_provides_s:
        provides.local_app_data = {
            "database": "foobar",
            "endpoints": "mysql-router-k8s.my-model.svc.cluster.local:6446",
            "read-only-endpoints": "mysql-router-k8s.my-model.svc.cluster.local:6447",
            "username": "foouser",
            "password": "foobar",
        }
    complete_requires = complete_requires.freeze()
    state = output_state(
        relations=[complete_requires, *complete_provides_s], event=complete_requires.broken_event
    )

    assert state.app_status == ops.BlockedStatus("Missing relation: backend-database")
    for index, provides in enumerate(complete_provides_s, 1):
        assert state.relations[index].local_app_data == {}


@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
def test_complete_requires_and_breaking_provides(complete_requires, complete_provides_s):
    for provides in complete_provides_s:
        provides.local_app_data = {
            "database": "foobar",
            "endpoints": "mysql-router-k8s.my-model.svc.cluster.local:6446",
            "read-only-endpoints": "mysql-router-k8s.my-model.svc.cluster.local:6447",
            "username": "foouser",
            "password": "foobar",
        }
    # Needed to access `.broken_event`
    complete_provides_s = [relation.freeze() for relation in complete_provides_s]

    state = output_state(
        relations=[complete_requires, *complete_provides_s],
        event=complete_provides_s[-1].broken_event,
    )
    if len(complete_provides_s) == 1:
        assert state.app_status == ops.BlockedStatus("Missing relation: database")
    else:
        assert state.app_status == ops.ActiveStatus()
    assert state.relations[-1].local_app_data == {}
    complete_provides_s.pop()
    for index, provides in enumerate(complete_provides_s, 1):
        assert state.relations[index].local_app_data == {
            "database": "foobar",
            "endpoints": "mysql-router-k8s.my-model.svc.cluster.local:6446",
            "read-only-endpoints": "mysql-router-k8s.my-model.svc.cluster.local:6447",
            "username": "foouser",
            "password": "foobar",
        }
