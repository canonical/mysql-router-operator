#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from pytest_operator.plugin import OpsTest

from .helpers import (
    execute_queries_on_unit,
    get_inserted_data_by_application,
    get_server_config_credentials,
)

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = "mysql"
MYSQL_ROUTER_APP_NAME = "mysqlrouter"
APPLICATION_APP_NAME = "mysql-test-app"
TEST_DATABASE = "continuous_writes_database"
TEST_TABLE = "random_data"
SLOW_TIMEOUT = 15 * 60


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_database_relation(ops_test: OpsTest, mysql_router_charm_series: str) -> None:
    """Test the database relation."""
    # Build and deploy applications
    mysqlrouter_charm = await ops_test.build_charm(".")

    app_charm = await ops_test.build_charm("./tests/integration/mysql-test-app/")

    # deploy mysqlrouter with num_units=None since it's a subordinate charm
    # and will be installed with the related consumer application
    applications = await asyncio.gather(
        ops_test.model.deploy(
            "mysql",
            channel="8.0/edge",
            application_name=MYSQL_APP_NAME,
            config={"profile": "testing"},
            num_units=1,
        ),
        ops_test.model.deploy(
            mysqlrouter_charm,
            application_name=MYSQL_ROUTER_APP_NAME,
            num_units=None,
        ),
        ops_test.model.deploy(
            app_charm,
            application_name=APPLICATION_APP_NAME,
            num_units=1,
            # MySQL Router is subordinate—it will use the series of the principal charm
            series=mysql_router_charm_series,
            channel="latest/edge",
        ),
    )

    mysql_app, application_app = applications[0], applications[2]

    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
    )

    # the mysqlrouter application will be in unknown state since it is a subordinate charm
    async with ops_test.fast_forward():
        await asyncio.gather(
            ops_test.model.wait_for_idle(
                apps=[MYSQL_APP_NAME],
                status="active",
                raise_on_blocked=True,
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.wait_for_idle(
                apps=[APPLICATION_APP_NAME],
                status="waiting",
                raise_on_blocked=True,
                timeout=SLOW_TIMEOUT,
            ),
        )

        await ops_test.model.relate(
            f"{MYSQL_ROUTER_APP_NAME}:database", f"{APPLICATION_APP_NAME}:database"
        )

        await ops_test.model.wait_for_idle(
            apps=[MYSQL_APP_NAME, MYSQL_ROUTER_APP_NAME, APPLICATION_APP_NAME],
            status="active",
            raise_on_blocked=True,
            timeout=SLOW_TIMEOUT,
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
    selected_data = await execute_queries_on_unit(
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

        await ops_test.model.wait_for_idle(
            apps=[MYSQL_APP_NAME, MYSQL_ROUTER_APP_NAME, APPLICATION_APP_NAME],
            status="active",
            raise_on_blocked=True,
            timeout=SLOW_TIMEOUT,
        )
