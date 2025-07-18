# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test charms subordinated alongside MySQL Router charm."""

import asyncio
import os

from .test_database import (
    APPLICATION_APP_NAME,
    MYSQL_APP_NAME,
    MYSQL_ROUTER_APP_NAME,
    SLOW_TIMEOUT,
)

UBUNTU_PRO_APP_NAME = "ubuntu-advantage"
LANDSCAPE_CLIENT_APP_NAME = "landscape-client"


async def test_ubuntu_pro(ops_test, charm, series):
    await asyncio.gather(
        ops_test.model.deploy(
            MYSQL_APP_NAME,
            channel="8.0/edge",
            application_name=MYSQL_APP_NAME,
            config={"profile": "testing"},
        ),
        ops_test.model.deploy(
            charm,
            application_name=MYSQL_ROUTER_APP_NAME,
            # deploy mysqlrouter with num_units=None since it's a subordinate charm
            num_units=None,
            series=series,
        ),
        ops_test.model.deploy(
            APPLICATION_APP_NAME,
            application_name=APPLICATION_APP_NAME,
            channel="latest/edge",
            # MySQL Router is subordinate—it will use the series of the principal charm
            series=series,
        ),
        ops_test.model.deploy(
            UBUNTU_PRO_APP_NAME,
            application_name=UBUNTU_PRO_APP_NAME,
            channel="latest/edge",
            config={"token": os.environ["UBUNTU_PRO_TOKEN"]},
            series=series,
        ),
    )
    await ops_test.model.relate(f"{MYSQL_APP_NAME}", f"{MYSQL_ROUTER_APP_NAME}")
    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:database", f"{APPLICATION_APP_NAME}:database"
    )
    await ops_test.model.relate(APPLICATION_APP_NAME, UBUNTU_PRO_APP_NAME)
    async with ops_test.fast_forward("60s"):
        await ops_test.model.wait_for_idle(
            apps=[
                MYSQL_APP_NAME,
                MYSQL_ROUTER_APP_NAME,
                APPLICATION_APP_NAME,
                UBUNTU_PRO_APP_NAME,
            ],
            status="active",
            raise_on_blocked=True,
            timeout=SLOW_TIMEOUT,
        )


async def test_landscape_client(ops_test, series):
    await ops_test.model.deploy(
        LANDSCAPE_CLIENT_APP_NAME,
        application_name=LANDSCAPE_CLIENT_APP_NAME,
        channel="latest/edge",
        config={
            "account-name": os.environ["LANDSCAPE_ACCOUNT_NAME"],
            "registration-key": os.environ["LANDSCAPE_REGISTRATION_KEY"],
            "ppa": "ppa:landscape/self-hosted-beta",
        },
        series=series,
    )
    await ops_test.model.relate(APPLICATION_APP_NAME, LANDSCAPE_CLIENT_APP_NAME)
    async with ops_test.fast_forward("60s"):
        await ops_test.model.wait_for_idle(
            apps=[
                MYSQL_APP_NAME,
                MYSQL_ROUTER_APP_NAME,
                APPLICATION_APP_NAME,
                LANDSCAPE_CLIENT_APP_NAME,
            ],
            status="active",
            raise_on_blocked=True,
            timeout=SLOW_TIMEOUT,
        )
