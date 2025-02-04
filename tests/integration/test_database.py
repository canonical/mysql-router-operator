#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from pytest_operator.plugin import OpsTest

from .helpers import (
    APPLICATION_DEFAULT_APP_NAME,
    MYSQL_DEFAULT_APP_NAME,
    MYSQL_ROUTER_DEFAULT_APP_NAME,
    execute_queries_against_unit,
    get_inserted_data_by_application,
    get_server_config_credentials,
)

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = MYSQL_DEFAULT_APP_NAME
MYSQL_ROUTER_APP_NAME = MYSQL_ROUTER_DEFAULT_APP_NAME
APPLICATION_APP_NAME = APPLICATION_DEFAULT_APP_NAME
TEST_DATABASE = "continuous_writes_database"
TEST_TABLE = "random_data"
SLOW_TIMEOUT = 15 * 60


@pytest.mark.abort_on_fail
async def test_database_relation(ops_test: OpsTest, charm, series) -> None:
    """Test the database relation."""
    # deploy mysqlrouter with num_units=None since it's a subordinate charm
    # and will be installed with the related consumer application
    applications = await asyncio.gather(
        ops_test.model.deploy(
            MYSQL_APP_NAME,
            channel="8.0/edge",
            application_name=MYSQL_APP_NAME,
            config={"profile": "testing"},
            num_units=1,
        ),
        ops_test.model.deploy(
            charm,
            application_name=MYSQL_ROUTER_APP_NAME,
            num_units=None,
        ),
        ops_test.model.deploy(
            APPLICATION_APP_NAME,
            application_name=APPLICATION_APP_NAME,
            num_units=1,
            # MySQL Router is subordinate—it will use the series of the principal charm
            series=series,
            channel="latest/edge",
        ),
    )

    [mysql_app, mysql_router_app, application_app] = applications

    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
    )

    # the mysqlrouter application will be in unknown state since it is a subordinate charm
    async with ops_test.fast_forward("60s"):
        await asyncio.gather(
            ops_test.model.block_until(
                lambda: mysql_app.status in ("active", "error", "blocked"),
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.block_until(
                lambda: application_app.status in ("waiting", "error", "blocked"),
                timeout=SLOW_TIMEOUT,
            ),
        )
        assert mysql_app.status == "active" and application_app.status == "waiting"

        await ops_test.model.relate(
            f"{MYSQL_ROUTER_APP_NAME}:database", f"{APPLICATION_APP_NAME}:database"
        )

        await ops_test.model.wait_for_idle(
            apps=[MYSQL_APP_NAME, MYSQL_ROUTER_APP_NAME, APPLICATION_APP_NAME],
            status="active",
            raise_on_blocked=True,
            timeout=SLOW_TIMEOUT,
        )

        await asyncio.gather(
            ops_test.model.block_until(
                lambda: mysql_app.status in ("active", "error", "blocked"),
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.block_until(
                lambda: mysql_router_app.status in ("active", "error", "blocked"),
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.block_until(
                lambda: application_app.status in ("active", "error", "blocked"),
                timeout=SLOW_TIMEOUT,
            ),
        )
        assert (
            mysql_app.status == "active"
            and mysql_router_app.status == "active"
            and application_app.status == "active"
        )

    # Ensure that the data inserted by sample application is present in the database
    application_unit = application_app.units[0]
    inserted_data = await get_inserted_data_by_application(application_unit)

    mysql_unit = mysql_app.units[0]
    mysql_unit_address = await mysql_unit.get_public_address()
    server_config_credentials = await get_server_config_credentials(mysql_unit)

    select_inserted_data_sql = (
        f"SELECT data FROM `{TEST_DATABASE}`.{TEST_TABLE} WHERE data = '{inserted_data}'",
    )
    selected_data = await execute_queries_against_unit(
        mysql_unit_address,
        server_config_credentials["username"],
        server_config_credentials["password"],
        select_inserted_data_sql,
    )

    assert inserted_data == selected_data[0]

    # Scale and ensure that all services go to active
    # (sample application tests that it can connect to its mysqlrouter service)
    async with ops_test.fast_forward():
        await application_app.add_unit()

        await ops_test.model.block_until(lambda: len(application_app.units) == 2)

        await asyncio.gather(
            ops_test.model.block_until(
                lambda: mysql_app.status in ("active", "error", "blocked"),
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.block_until(
                lambda: mysql_router_app.status in ("active", "error", "blocked"),
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.block_until(
                lambda: application_app.status in ("active", "error", "blocked"),
                timeout=SLOW_TIMEOUT,
            ),
        )
        assert (
            mysql_app.status == "active"
            and mysql_router_app.status == "active"
            and application_app.status == "active"
        )
