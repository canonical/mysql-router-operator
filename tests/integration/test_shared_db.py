#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = "mysql"
KEYSTONE_APP_NAME = "keystone"
MYSQLROUTER_APP_NAME = "mysqlrouter"
TIMEOUT = 15 * 60


@pytest.mark.order(1)
@pytest.mark.abort_on_fail
@pytest.mark.shared_db_tests
async def test_shared_db(ops_test: OpsTest):
    """Test the shared-db legacy relation."""
    charm = await ops_test.build_charm(".")

    mysql_app = await ops_test.model.deploy(
        "mysql", channel="latest/edge", application_name=MYSQL_APP_NAME, num_units=1
    )
    keystone_app = await ops_test.model.deploy(
        "keystone", application_name=KEYSTONE_APP_NAME, series="focal", num_units=2
    )
    mysqlrouter_app = await ops_test.model.deploy(
        charm, application_name=MYSQLROUTER_APP_NAME, num_units=None
    )

    await ops_test.model.relate(
        f"{KEYSTONE_APP_NAME}:shared-db", f"{MYSQLROUTER_APP_NAME}:shared-db"
    )

    async with ops_test.fast_forward():
        await asyncio.gather(
            ops_test.model.wait_for_idle(
                apps=[MYSQL_APP_NAME],
                status="active",
                raise_on_blocked=True,
                timeout=TIMEOUT,
                wait_for_exact_units=1,
            ),
            ops_test.model.wait_for_idle(
                apps=[KEYSTONE_APP_NAME],
                status="blocked",
                raise_on_blocked=False,
                timeout=TIMEOUT,
                wait_for_exact_units=2,
            ),
            ops_test.model.wait_for_idle(
                apps=[MYSQLROUTER_APP_NAME],
                status="waiting",
                raise_on_blocked=True,
                timeout=TIMEOUT,
            ),
        )

    await ops_test.model.relate(f"{MYSQLROUTER_APP_NAME}:database", f"{MYSQL_APP_NAME}:database")

    async with ops_test.fast_forward():
        await asyncio.gather(
            ops_test.model.block_until(lambda: mysql_app.status == "active", timeout=TIMEOUT),
            ops_test.model.block_until(lambda: keystone_app.status == "active", timeout=TIMEOUT),
            ops_test.model.block_until(
                lambda: mysqlrouter_app.status == "active", timeout=TIMEOUT
            ),
        )
