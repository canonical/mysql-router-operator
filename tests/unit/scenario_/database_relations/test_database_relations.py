# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test app status and relation databags"""

import typing

import ops
import pytest
import scenario

import kubernetes_charm

from ..wrapper import Relation
from . import combinations


@pytest.fixture(params=["my-model.svc.cluster.local", "foo.svc.cluster.local"])
def model_service_domain(monkeypatch, request):
    monkeypatch.setattr(
        "kubernetes_charm.KubernetesRouterCharm.model_service_domain", request.param
    )
    return request.param


def output_states(
    *, relations: list[Relation | scenario.Relation]
) -> typing.Iterable[scenario.State]:
    """Run scenario test for each `abstract_charm.reconcile_database_relations` event.

    Excludes *-relation-breaking events

    The output state of each test should be identical for all events.
    """
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
    events = [container.pebble_ready_event]
    for relation in relations:
        events.extend(
            (
                relation.created_event,
                # data_interfaces lib does not always emit event (to charm) on *-relation-changed
                # relation.changed_event,
            )
        )
    for event in events:
        yield context.run(event, input_state)


# Tests are ordered by status priority.
# For example, `ops.BlockedStatus("Missing relation: backend-database")` has priority over
# `ops.BlockedStatus("Missing relation: database")`.
# Therefore, the test for `ops.BlockedStatus("Missing relation: database")` depends on a
# database_requires relation.
# Tests are ordered from least to most dependencies.


def test_missing_requires():
    for state in output_states(relations=[]):
        assert state.app_status == ops.BlockedStatus("Missing relation: backend-database")


def test_missing_provides(incomplete_requires):
    for state in output_states(relations=[incomplete_requires]):
        assert state.app_status == ops.BlockedStatus("Missing relation: database")


@pytest.mark.parametrize(
    "unsupported_extra_user_role_provides_s",
    combinations.unsupported_extra_user_role_provides(1, 3),
)
@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(0, 2))
def test_provides_unsupported_extra_user_role(
    incomplete_requires, complete_provides_s, unsupported_extra_user_role_provides_s
):
    for state in output_states(
        relations=[
            incomplete_requires,
            *complete_provides_s,
            *unsupported_extra_user_role_provides_s,
        ]
    ):
        assert state.app_status == ops.BlockedStatus(
            f"{unsupported_extra_user_role_provides_s[0].remote_app_name} app requested unsupported extra user role on database endpoint"
        )


@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 2))
def test_incomplete_requires(incomplete_requires, complete_provides_s):
    for state in output_states(relations=[incomplete_requires, *complete_provides_s]):
        assert state.app_status == ops.WaitingStatus(
            f"Waiting for {incomplete_requires.remote_app_name} app on backend-database endpoint"
        )
        for index, provides in enumerate(complete_provides_s, 1):
            assert state.relations[index].local_app_data == {}


@pytest.mark.parametrize(
    "unsupported_extra_user_role_provides_s",
    combinations.unsupported_extra_user_role_provides(1, 3),
)
@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(0, 2))
def test_complete_requires_and_provides_unsupported_extra_user_role(
    complete_requires,
    complete_provides_s,
    unsupported_extra_user_role_provides_s,
    model_service_domain,
):
    # Needed to access `.relation_id`
    complete_provides_s = [relation.freeze() for relation in complete_provides_s]

    for state in output_states(
        relations=[
            complete_requires,
            *complete_provides_s,
            *unsupported_extra_user_role_provides_s,
        ]
    ):
        assert state.app_status == ops.BlockedStatus(
            f"{unsupported_extra_user_role_provides_s[0].remote_app_name} app requested unsupported extra user role on database endpoint"
        )
        for index, provides in enumerate(complete_provides_s, 1):
            local_app_data = state.relations[index].local_app_data
            assert len(local_app_data.pop("password")) > 0
            assert local_app_data == {
                "database": provides.remote_app_data["database"],
                "endpoints": f"mysql-router-k8s.{model_service_domain}:6446",
                "read-only-endpoints": f"mysql-router-k8s.{model_service_domain}:6447",
                "username": f'{complete_requires.remote_app_data["username"]}-{provides.relation_id}',
            }
        for index, provides in enumerate(
            unsupported_extra_user_role_provides_s, 1 + len(complete_provides_s)
        ):
            assert state.relations[index].local_app_data == {}


@pytest.mark.parametrize("incomplete_provides_s", combinations.incomplete_provides(1, 3))
def test_incomplete_provides(complete_requires, incomplete_provides_s):
    for state in output_states(relations=[complete_requires, *incomplete_provides_s]):
        assert state.app_status == ops.WaitingStatus(
            f"Waiting for {incomplete_provides_s[0].remote_app_name} app on database endpoint"
        )
        for index, provides in enumerate(incomplete_provides_s, 1):
            assert state.relations[index].local_app_data == {}


@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 2, 4))
def test_complete_provides(complete_requires, complete_provides_s, model_service_domain):
    # Needed to access `.relation_id`
    complete_provides_s = [relation.freeze() for relation in complete_provides_s]

    for state in output_states(relations=[complete_requires, *complete_provides_s]):
        assert state.app_status == ops.ActiveStatus()
        for index, provides in enumerate(complete_provides_s, 1):
            local_app_data = state.relations[index].local_app_data
            assert len(local_app_data.pop("password")) > 0
            assert local_app_data == {
                "database": provides.remote_app_data["database"],
                "endpoints": f"mysql-router-k8s.{model_service_domain}:6446",
                "read-only-endpoints": f"mysql-router-k8s.{model_service_domain}:6447",
                "username": f'{complete_requires.remote_app_data["username"]}-{provides.relation_id}',
            }


@pytest.mark.parametrize("incomplete_provides_s", combinations.incomplete_provides(1, 3))
@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
def test_complete_provides_and_incomplete_provides(
    complete_requires, complete_provides_s, incomplete_provides_s, model_service_domain
):
    # Needed to access `.relation_id`
    complete_provides_s = [relation.freeze() for relation in complete_provides_s]

    for state in output_states(
        relations=[complete_requires, *complete_provides_s, *incomplete_provides_s]
    ):
        assert state.app_status == ops.WaitingStatus(
            f"Waiting for {incomplete_provides_s[0].remote_app_name} app on database endpoint"
        )
        for index, provides in enumerate(complete_provides_s, 1):
            local_app_data = state.relations[index].local_app_data
            assert len(local_app_data.pop("password")) > 0
            assert local_app_data == {
                "database": provides.remote_app_data["database"],
                "endpoints": f"mysql-router-k8s.{model_service_domain}:6446",
                "read-only-endpoints": f"mysql-router-k8s.{model_service_domain}:6447",
                "username": f'{complete_requires.remote_app_data["username"]}-{provides.relation_id}',
            }
        for index, provides in enumerate(incomplete_provides_s, 1 + len(complete_provides_s)):
            assert state.relations[index].local_app_data == {}
