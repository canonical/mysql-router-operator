# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Generate `Relation` combinations for `pytest.mark.parameterize`."""

import itertools
import typing

from ..wrapper import Relation


def _relation_combinations(
    *, relation_amounts: typing.Iterable[int], relations: list[Relation]
) -> list[typing.Iterable[Relation]]:
    """Get all combinations of `relations` for each length in `relation_amounts`."""
    combinations = []
    for number_of_relations in relation_amounts:
        for combination in itertools.combinations_with_replacement(relations, number_of_relations):
            combination: tuple[Relation]
            combinations.append(combination)
    return combinations


def incomplete_provides(*relation_amounts: int) -> list[typing.Iterable[Relation]]:
    databags = [{}]
    relations = []
    for remote_app_name in ["remote", "mysql-test-app"]:
        relations.extend(
            _relation_combinations(
                relation_amounts=relation_amounts,
                relations=[
                    Relation(
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
) -> list[typing.Iterable[Relation]]:
    databags = [
        {"database": "myappA", "extra-user-roles": "admin"},
        {"database": "myappB", "extra-user-roles": "mysqlrouter"},
    ]
    return _relation_combinations(
        relation_amounts=relation_amounts,
        relations=[Relation(endpoint="database", remote_app_data=databag) for databag in databags],
    )


def complete_provides(*relation_amounts: int) -> list[typing.Iterable[Relation]]:
    databags = [{"database": "myappA"}, {"database": "foo"}]
    return _relation_combinations(
        relation_amounts=relation_amounts,
        relations=[Relation(endpoint="database", remote_app_data=databag) for databag in databags],
    )
