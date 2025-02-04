#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio

from pytest_operator.plugin import OpsTest

from . import markers
from .helpers import get_charm

MYSQL_ROUTER_APP_NAME = "mysql-router"
MYSQL_TEST_APP_NAME = "mysql-test-app"


@markers.amd64_only
async def test_arm_charm_on_amd_host(ops_test: OpsTest, ubuntu_base) -> None:
    """Tries deploying an arm64 charm on amd64 host."""
    charm = await get_charm(".", "arm64", 2)

    await asyncio.gather(
        ops_test.model.deploy(
            charm,
            application_name=MYSQL_ROUTER_APP_NAME,
            num_units=0,
            base=f"ubuntu@{ubuntu_base}",
        ),
        ops_test.model.deploy(
            MYSQL_TEST_APP_NAME,
            application_name=MYSQL_TEST_APP_NAME,
            num_units=1,
            channel="latest/edge",
            base=f"ubuntu@{ubuntu_base}",
        ),
    )

    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:database",
        f"{MYSQL_TEST_APP_NAME}:database",
    )

    await ops_test.model.wait_for_idle(
        apps=[MYSQL_ROUTER_APP_NAME],
        status="error",
        raise_on_error=False,
    )


@markers.arm64_only
async def test_amd_charm_on_arm_host(ops_test: OpsTest, ubuntu_base) -> None:
    """Tries deploying an amd64 charm on arm64 host."""
    charm = await get_charm(".", "amd64", 1)

    await asyncio.gather(
        ops_test.model.deploy(
            charm,
            application_name=MYSQL_ROUTER_APP_NAME,
            num_units=0,
            base=f"ubuntu@{ubuntu_base}",
        ),
        ops_test.model.deploy(
            MYSQL_TEST_APP_NAME,
            application_name=MYSQL_TEST_APP_NAME,
            num_units=1,
            channel="latest/edge",
            base=f"ubuntu@{ubuntu_base}",
        ),
    )

    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:database",
        f"{MYSQL_TEST_APP_NAME}:database",
    )

    await ops_test.model.wait_for_idle(
        apps=[MYSQL_ROUTER_APP_NAME],
        status="error",
        raise_on_error=False,
    )
