# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test app status and relation databags"""

import typing

import ops
import pytest
import scenario

import charm

from . import combinations


def output_states(*, relations: list[scenario.Relation]) -> typing.Iterable[scenario.State]:
    """Run scenario test for each `abstract_charm.reconcile_database_relations` event.

    Excludes *-relation-breaking events

    The output state of each test should be identical for all events.
    """
    context = scenario.Context(charm.MachineSubordinateRouterCharm)
    input_state = scenario.State(
        relations=[*relations, scenario.PeerRelation(endpoint="refresh-v-three")],
        leader=True,
    )
    events = []
    for relation in relations:
        events.extend((
            relation.created_event,
            # data_interfaces lib does not always emit event (to charm) on *-relation-changed
            # relation.changed_event,
        ))
    for event in events:
        output = context.run(event, input_state)
        output.relations.pop()  # Remove PeerRelation
        yield output


def assert_complete_local_app_databag(
    local_app_data: dict[str, str],
    secrets: list[scenario.Secret],
    complete_requires: scenario.Relation,
    provides: scenario.Relation,
    juju_has_secrets: bool,
):
    if juju_has_secrets and "requested-secrets" in provides.remote_app_data:
        secret_id = local_app_data.pop("secret-user")
        secrets_ = [secret for secret in secrets if secret.id == secret_id]
        assert len(secrets_) == 1
        secret = secrets_[0]
        contents = secret.contents.pop(0)  # Revision 0
        assert len(secret.contents) == 0  # Only 1 revision should exist
        assert len(contents.pop("password")) > 0
        assert contents == {
            "username": f"{complete_requires.remote_app_data['username']}-{provides.relation_id}"
        }
    else:
        assert len(local_app_data.pop("password")) > 0
        assert (
            local_app_data.pop("username")
            == f"{complete_requires.remote_app_data['username']}-{provides.relation_id}"
        )
    assert local_app_data == {
        "database": provides.remote_app_data["database"],
        "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
        "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
    }


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
    juju_has_secrets,
):
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
            assert_complete_local_app_databag(
                local_app_data, state.secrets, complete_requires, provides, juju_has_secrets
            )
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
def test_complete_provides(complete_requires, complete_provides_s, juju_has_secrets):
    for state in output_states(relations=[complete_requires, *complete_provides_s]):
        assert state.app_status == ops.ActiveStatus()
        for index, provides in enumerate(complete_provides_s, 1):
            local_app_data = state.relations[index].local_app_data
            assert_complete_local_app_databag(
                local_app_data, state.secrets, complete_requires, provides, juju_has_secrets
            )


@pytest.mark.parametrize("incomplete_provides_s", combinations.incomplete_provides(1, 3))
@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
def test_complete_provides_and_incomplete_provides(
    complete_requires, complete_provides_s, incomplete_provides_s, juju_has_secrets
):
    for state in output_states(
        relations=[complete_requires, *complete_provides_s, *incomplete_provides_s]
    ):
        assert state.app_status == ops.WaitingStatus(
            f"Waiting for {incomplete_provides_s[0].remote_app_name} app on database endpoint"
        )
        for index, provides in enumerate(complete_provides_s, 1):
            local_app_data = state.relations[index].local_app_data
            assert_complete_local_app_databag(
                local_app_data, state.secrets, complete_requires, provides, juju_has_secrets
            )
        for index, provides in enumerate(incomplete_provides_s, 1 + len(complete_provides_s)):
            assert state.relations[index].local_app_data == {}
