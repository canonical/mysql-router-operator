# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test app status and relation databags"""

import ops
import pytest
import scenario

import machine_charm

from . import combinations


def output_state(
    *,
    relations: list[scenario.Relation],
    event: scenario.Event,
    secrets: list[scenario.Secret] = [],
) -> scenario.State:
    context = scenario.Context(machine_charm.MachineSubordinateRouterCharm)
    input_state = scenario.State(
        relations=relations,
        secrets=secrets,
        leader=True,
    )
    return context.run(event, input_state)


@pytest.mark.usefixtures("only_without_juju_secrets")
@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
def test_breaking_requires_and_complete_provides(complete_requires, complete_provides_s):
    complete_provides_s = [
        relation.replace(
            local_app_data={
                "database": "foobar",
                "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                "username": "foouser",
                "password": "foobar",
            }
        )
        for relation in complete_provides_s
    ]
    state = output_state(
        relations=[complete_requires, *complete_provides_s], event=complete_requires.broken_event
    )
    assert state.app_status == ops.BlockedStatus("Missing relation: backend-database")
    for index, provides in enumerate(complete_provides_s, 1):
        assert state.relations[index].local_app_data == {}


@pytest.mark.usefixtures("only_with_juju_secrets")
@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
@pytest.mark.parametrize(
    "complete_requires_s, secret", combinations.complete_requires_secret(1, 2, 4)
)
def test_breaking_requires_and_complete_provides_secret(
    complete_requires_s, secret, complete_provides_s
):
    complete_provides_s = [
        relation.replace(
            local_app_data={
                "database": "foobar",
                "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                "username": "foouser",
                "password": "foobar",
            }
        )
        for relation in complete_provides_s
    ]
    state = output_state(
        relations=[complete_requires_s, *complete_provides_s],
        event=complete_requires_s.broken_event,
        secrets=[secret],
    )
    assert state.app_status == ops.BlockedStatus("Missing relation: backend-database")
    for index, provides in enumerate(complete_provides_s, 1):
        assert state.relations[index].local_app_data == {}


@pytest.mark.usefixtures("only_without_juju_secrets")
@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
def test_complete_requires_and_breaking_provides(complete_requires, complete_provides_s):
    complete_provides_s = [
        relation.replace(
            local_app_data={
                "database": "foobar",
                "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                "username": "foouser",
                "password": "foobar",
            }
        )
        for relation in complete_provides_s
    ]
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
            "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
            "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
            "username": "foouser",
            "password": "foobar",
        }


@pytest.mark.usefixtures("only_with_juju_secrets")
@pytest.mark.parametrize("complete_provides_s", combinations.complete_provides(1, 3))
@pytest.mark.parametrize(
    "complete_requires_s, secret", combinations.complete_requires_secret(1, 2, 4)
)
def test_complete_requires_and_breaking_provides_secret(
    complete_requires_s, secret, complete_provides_s
):
    complete_provides_s = [
        relation.replace(
            local_app_data={
                "database": "foobar",
                "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
                "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
                "username": "foouser",
                "password": "foobar",
            }
        )
        for relation in complete_provides_s
    ]
    state = output_state(
        relations=[complete_requires_s, *complete_provides_s],
        event=complete_provides_s[-1].broken_event,
        secrets=[secret],
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
            "endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
            "read-only-endpoints": "file:///var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock",
            "username": "foouser",
            "password": "foobar",
        }
