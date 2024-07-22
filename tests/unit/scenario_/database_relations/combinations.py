# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Generate `Relation` combinations for `pytest.mark.parameterize`."""

import itertools
import typing
from uuid import uuid4

import scenario

APP_NAMES = ["remote", "mysql-k8s"]
SECRET_USER = scenario.Secret(
    id="myXID",  # Must be defined for obj instantiation, but we override it later
    owner="mysql-router",
    contents={0: {"username": "relation-68", "password": "Dy0k2UTfyNt2B13cfe412K7YGs07S4U7"}},
    remote_grants="myappB",
)


def _relation_provides_combinations(
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


def _relation_requires_combinations(
    *,
    relation_amounts: typing.Iterable[int],
    relations: list[scenario.Relation],
    secrets: list[scenario.Secret],
) -> list[list[scenario.Relation]]:
    """Get all combinations of `relations` for each length in `relation_amounts`."""
    combinations = []
    for number_of_relations in relation_amounts:
        for combination in itertools.combinations_with_replacement(relations, number_of_relations):
            combination: tuple[scenario.Relation]

            for relation in combination:
                secret_id = uuid4().hex
                relation_id = scenario.state.next_relation_id()

                secrets_new = [
                    secret.replace(
                        id=secret_id, label=f"{relation.endpoint}.{relation_id}.user.secret"
                    )
                    for secret in secrets
                ]

                remote_app_data_new = relation.remote_app_data
                remote_app_data_new["secret-user"] = secret_id
                combinations += [
                    (
                        relation.replace(
                            relation_id=relation_id, remote_app_data=remote_app_data_new
                        ),
                        secret_new,
                    )
                    for secret_new in secrets_new
                ]
    return combinations


def incomplete_provides(*relation_amounts: int) -> list[list[scenario.SubordinateRelation]]:
    databags = [{}]
    relations = []
    for remote_app_name in ["remote", "mysql-test-app"]:
        relations.extend(
            _relation_provides_combinations(
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
    ]
    return _relation_provides_combinations(
        relation_amounts=relation_amounts,
        relations=[
            scenario.SubordinateRelation(endpoint="database", remote_app_data=databag)
            for databag in databags
        ],
    )


def complete_provides(*relation_amounts: int) -> list[list[scenario.SubordinateRelation]]:
    databags = [{"database": "myappA"}, {"database": "foo"}]
    return _relation_provides_combinations(
        relation_amounts=relation_amounts,
        relations=[
            scenario.SubordinateRelation(endpoint="database", remote_app_data=databag)
            for databag in databags
        ],
    )


def complete_requires_secret(*relation_amounts: int) -> list[list[scenario.Relation]]:
    relation = scenario.Relation(
        endpoint="backend-database",
        remote_app_data={
            "endpoints": "mysql-k8s-primary:5432"
        },  # Will be extended with "secret-user" field
    )
    return _relation_requires_combinations(
        relation_amounts=relation_amounts, relations=[relation], secrets=[SECRET_USER]
    )


def incomplete_requires_secret(*relation_amounts: int) -> list[list[scenario.Relation]]:
    params = [
        {},
        {
            "database": "myappB",
            "read-only-endpoints": "mysql-k8s-replicas:5432",
        },
        {
            "database": "myappB",
            "endpoints": "mysql-k8s-primary:5432",
            "read-only-endpoints": "mysql-k8s-replicas:5432",
        },
    ]

    # Missing fields in the databag
    relations = [
        scenario.Relation(
            endpoint="backend-database",
            remote_app_name=app_name,
            remote_app_data=param,  # Will be extended with "secret-user" field
        )
        for app_name in APP_NAMES
        for param in params[:2]
    ]
    combinations_full_secret = _relation_requires_combinations(
        relation_amounts=relation_amounts, relations=relations, secrets=[SECRET_USER]
    )

    # Missing fields in the secret
    secret_user_pw_missing = SECRET_USER.replace(contents={0: {"username": "relation-68"}})

    relations_broken_secret = [
        scenario.Relation(
            endpoint="backend-database",
            remote_app_name=app_name,
            remote_app_data=params[2],  # Will be extended with "secret-user" field
        )
        for app_name in APP_NAMES
    ]

    combinations_broken_secret = _relation_requires_combinations(
        relation_amounts=relation_amounts,
        relations=relations_broken_secret,
        secrets=[secret_user_pw_missing],
    )

    return combinations_full_secret + combinations_broken_secret
