# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
import scenario


@pytest.fixture(params=["remote", "mysql-k8s"])
def app_name(request):
    return request.param


@pytest.fixture(
    params=[
        {},
        {
            "database": "myappB",
            "read-only-endpoints": "mysql-k8s-replicas:5432",
            "password": "Dy0k2UTfyNt2B13cfe412K7YGs07S4U7",
            "username": "relation-68",
        },
        {
            "database": "myappB",
            "endpoints": "mysql-k8s-primary:5432",
            "read-only-endpoints": "mysql-k8s-replicas:5432",
            "username": "relation-68",
        },
    ]
)
def incomplete_requires(app_name, request) -> scenario.Relation:
    return scenario.Relation(
        endpoint="backend-database", remote_app_name=app_name, remote_app_data=request.param
    )


@pytest.fixture
def complete_requires() -> scenario.Relation:
    return scenario.Relation(
        endpoint="backend-database",
        remote_app_data={
            "endpoints": "mysql-k8s-primary:5432",
            "password": "Dy0k2UTfyNt2B13cfe412K7YGs07S4U7",
            "username": "relation-68",
        },
    )
