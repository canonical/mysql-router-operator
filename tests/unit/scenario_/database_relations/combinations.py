# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Generate `Relation` combinations for `pytest.mark.parameterize`."""

import itertools
import typing

import scenario


def _relation_combinations(
    *, relation_amounts: typing.Iterable[int], relations: list[scenario.SubordinateRelation]
) -> list[list[scenario.SubordinateRelation]]:
    """Get all combinations of `relations` for each length in `relation_amounts`."""
    combinations = []
    for number_of_relations in relation_amounts:
        for combination in itertools.combinations_with_replacement(relations, number_of_relations):
            combination: tuple[scenario.SubordinateRelation]
            combinations.append([
                relation.replace(relation_id=scenario.state.next_relation_id())
                for relation in combination
            ])
    return combinations


def incomplete_provides(*relation_amounts: int) -> list[list[scenario.SubordinateRelation]]:
    databags = [{}]
    relations = []
    for remote_app_name in ["remote", "mysql-test-app"]:
        relations.extend(
            _relation_combinations(
                relation_amounts=relation_amounts,
                relations=[
                    scenario.SubordinateRelation(
                        endpoint="database",
                        remote_app_name=remote_app_name,
                        remote_app_data=databag,
                    )
                    for databag in databags
                ],
            )
        )
    return relations


def unsupported_extra_user_role_provides(
    *relation_amounts: int,
) -> list[list[scenario.SubordinateRelation]]:
    databags = [
        {"database": "myappA", "extra-user-roles": "admin"},
        {"database": "myappB", "extra-user-roles": "mysqlrouter"},
        {
            "database": "myappA",
            "extra-user-roles": "admin",
            "requested-secrets": '["username", "password", "tls", "tls-ca", "uris"]',
        },
    ]
    return _relation_combinations(
        relation_amounts=relation_amounts,
        relations=[
            scenario.SubordinateRelation(endpoint="database", remote_app_data=databag)
            for databag in databags
        ],
    )


def complete_provides(*relation_amounts: int) -> list[list[scenario.SubordinateRelation]]:
    databags = [
        {"database": "myappA"},
        {"database": "foo"},
        {
            "database": "myappA",
            "requested-secrets": '["username", "password", "tls", "tls-ca", "uris"]',
        },
    ]
    return _relation_combinations(
        relation_amounts=relation_amounts,
        relations=[
            scenario.SubordinateRelation(endpoint="database", remote_app_data=databag)
            for databag in databags
        ],
    )
