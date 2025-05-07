# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test app status and relation databags"""

import ops
import pytest
import scenario

import charm

from . import combinations


def output_state(
    *, relations: list[scenario.Relation], secrets: list[scenario.Secret], event: scenario.Event
) -> scenario.State:
    context = scenario.Context(charm.MachineSubordinateRouterCharm)
    input_state = scenario.State(
        relations=[*relations, scenario.PeerRelation(endpoint="refresh-v-three")],
        secrets=secrets,
        leader=True,
    )
    output = context.run(event, input_state)
    output.relations.pop()  # Remove PeerRelation
    return output


@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
def test_breaking_requires_and_complete_provides(
    complete_requires, complete_provides_s, juju_has_secrets
):
    complete_provides_s_ = []
    secrets = []
    for relation in complete_provides_s:
        relation: scenario.Relation
        if juju_has_secrets and "requested-secrets" in relation.remote_app_data:
            secret = scenario.Secret(
                id="foo",
                contents={0: {"username": "foouser", "password": "foobar"}},
                owner="application",
            )
            relation = relation.replace(
                local_app_data={
                    "database": "foobar",
                    "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                    "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                    "secret-user": secret.id,
                }
            )
            secrets.append(secret)
        else:
            relation = relation.replace(
                local_app_data={
                    "database": "foobar",
                    "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                    "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                    "username": "foouser",
                    "password": "foobar",
                }
            )
        complete_provides_s_.append(relation)
    state = output_state(
        relations=[complete_requires, *complete_provides_s_],
        secrets=secrets,
        event=complete_requires.broken_event,
    )
    assert state.app_status == ops.BlockedStatus("Missing relation: backend-database")
    for index, provides in enumerate(complete_provides_s_, 1):
        local_app_data = state.relations[index].local_app_data
        # TODO secrets cleanup: remove
        # (waiting on https://github.com/canonical/data-platform-libs/issues/118)
        local_app_data.pop("secret-user", None)
        assert local_app_data == {}
        # TODO secrets cleanup: test if secrets deleted
        # (waiting on https://github.com/canonical/data-platform-libs/issues/118)
        # assert len(state.secrets) == 0  # use a better check here—other secrets could exist


@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
def test_complete_requires_and_breaking_provides(
    complete_requires, complete_provides_s, juju_has_secrets
):
    complete_provides_s_ = []
    secrets = []
    for relation in complete_provides_s:
        relation: scenario.Relation
        if juju_has_secrets and "requested-secrets" in relation.remote_app_data:
            secret = scenario.Secret(
                id=f"foo-{relation.relation_id}",
                contents={0: {"username": "foouser", "password": "foobar"}},
                owner="application",
            )
            relation = relation.replace(
                local_app_data={
                    "database": "foobar",
                    "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                    "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                    "secret-user": secret.id,
                }
            )
            secrets.append(secret)
        else:
            relation = relation.replace(
                local_app_data={
                    "database": "foobar",
                    "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                    "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                    "username": "foouser",
                    "password": "foobar",
                }
            )
        complete_provides_s_.append(relation)
    state = output_state(
        relations=[complete_requires, *complete_provides_s_],
        event=complete_provides_s_[-1].broken_event,
        secrets=secrets,
    )
    if len(complete_provides_s_) == 1:
        assert state.app_status == ops.BlockedStatus("Missing relation: database")
    else:
        assert state.app_status == ops.ActiveStatus()
    local_app_data = state.relations[-1].local_app_data
    # TODO secrets cleanup: remove
    # (waiting on https://github.com/canonical/data-platform-libs/issues/118)
    local_app_data.pop("secret-user", None)
    assert local_app_data == {}
    # TODO secrets cleanup: test if secret deleted
    # (waiting on https://github.com/canonical/data-platform-libs/issues/118)
    complete_provides_s_.pop()
    for index, provides in enumerate(complete_provides_s_, 1):
        relation = state.relations[index]
        if juju_has_secrets and "requested-secrets" in relation.remote_app_data:
            local_app_data = relation.local_app_data
            secret_id = local_app_data.pop("secret-user")
            secrets = [secret for secret in state.secrets if secret.id == secret_id]
            assert len(secrets) == 1
            contents = secrets[0].contents
            rev_contents = contents.pop(0)
            assert len(contents) == 0
            assert rev_contents == {"username": "foouser", "password": "foobar"}
            assert local_app_data == {
                "database": "foobar",
                "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
            }
        else:
            assert relation.local_app_data == {
                "database": "foobar",
                "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                "username": "foouser",
                "password": "foobar",
            }
