#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from pytest_operator.plugin import OpsTest

from .helpers import get_charm

MYSQL_ROUTER_APP_NAME = "mysql-router"


@pytest.mark.group(1)
@pytest.mark.usefixtures("only_amd64")
async def test_arm_charm_on_amd_host(ops_test: OpsTest) -> None:
    """Tries deploying an arm64 charm on amd64 host."""
    charm = await get_charm(".", "arm64", 2)

    await ops_test.model.deploy(
        charm,
        application_name=MYSQL_ROUTER_APP_NAME,
        num_units=0,
        base="ubuntu@22.04",
    )

    await ops_test.model.wait_for_idle(
        apps=[MYSQL_ROUTER_APP_NAME],
        status="error",
        raise_on_error=False,
    )


@pytest.mark.group(1)
@pytest.mark.usefixtures("only_arm64")
async def test_amd_charm_on_arm_host(ops_test: OpsTest) -> None:
    """Tries deploying an amd64 charm on arm64 host."""
    charm = await get_charm(".", "amd64", 1)

    await ops_test.model.deploy(
        charm,
        application_name=MYSQL_ROUTER_APP_NAME,
        num_units=0,
        base="ubuntu@22.04",
    )

    await ops_test.model.wait_for_idle(
        apps=[MYSQL_ROUTER_APP_NAME],
        status="error",
        raise_on_error=False,
    )
