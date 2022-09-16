#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from helpers import (
    execute_queries_on_unit,
    get_inserted_data_by_application,
    get_server_config_credentials,
)
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = "mysql"
MYSQL_ROUTER_APP_NAME = "mysqlrouter"
APPLICATION_APP_NAME = "application"
SLOW_TIMEOUT = 15 * 60


@pytest.mark.order(1)
@pytest.mark.abort_on_fail
@pytest.mark.database_tests
async def test_database_relation(ops_test: OpsTest) -> None:
    """Test the database relation."""
    # Build and deploy applications
    mysqlrouter_charm = await ops_test.build_charm(".")
    application_charm = await ops_test.build_charm("./tests/integration/application-charm/")

    mysql_app = await ops_test.model.deploy(
        "mysql", channel="latest/edge", application_name=MYSQL_APP_NAME, num_units=1
    )

    mysqlrouter_app = await ops_test.model.deploy(
        mysqlrouter_charm, application_name=MYSQL_ROUTER_APP_NAME, num_units=None
    )

    application_app = await ops_test.model.deploy(
        application_charm, application_name=APPLICATION_APP_NAME, num_units=1
    )

    await ops_test.model.relate(
        f"{APPLICATION_APP_NAME}:database", f"{MYSQL_ROUTER_APP_NAME}:database"
    )

    async with ops_test.fast_forward():
        await asyncio.gather(
            ops_test.model.block_until(
                lambda: mysql_app.status in ("active", "blocked", "error"), timeout=SLOW_TIMEOUT
            ),
            ops_test.model.block_until(
                lambda: mysqlrouter_app.status in ("waiting", "blocked", "error"),
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.block_until(
                lambda: application_app.status in ("waiting", "error"), timeout=SLOW_TIMEOUT
            ),
        )

        assert (
            mysql_app.status == "active"
            and mysqlrouter_app.status == "waiting"
            and application_app.status == "waiting"
        )

        await ops_test.model.relate(
            f"{MYSQL_ROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
        )

        await asyncio.gather(
            ops_test.model.block_until(
                lambda: mysql_app.status in ("active", "blocked", "error"), timeout=SLOW_TIMEOUT
            ),
            ops_test.model.block_until(
                lambda: mysqlrouter_app.status in ("active", "blocked", "error"),
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.block_until(
                lambda: application_app.status in ("active", "error"), timeout=SLOW_TIMEOUT
            ),
        )

        assert (
            mysql_app.status == "active"
            and mysqlrouter_app.status == "active"
            and application_app.status == "active"
        )

    # Ensure that the data inserted by sample application is present in the database
    application_unit = application_app.units[0]
    inserted_data = await get_inserted_data_by_application(application_unit)

    mysql_unit = mysql_app.units[0]
    mysql_unit_address = await mysql_unit.get_public_address()
    server_config_credentials = await get_server_config_credentials(mysql_unit)

    select_inserted_data_sql = (
        f"SELECT data FROM application_test_database.app_data WHERE data = '{inserted_data}'",
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

        ops_test.model.block_until(lambda: len(application_app.units) == 2)

        await asyncio.gather(
            ops_test.model.block_until(
                lambda: mysql_app.status in ("active", "blocked", "error"), timeout=SLOW_TIMEOUT
            ),
            ops_test.model.block_until(
                lambda: mysqlrouter_app.status in ("active", "blocked", "error"),
                timeout=SLOW_TIMEOUT,
            ),
            ops_test.model.block_until(
                lambda: application_app.status in ("active", "error"), timeout=SLOW_TIMEOUT
            ),
        )

        assert (
            mysql_app.status == "active"
            and mysqlrouter_app.status == "active"
            and application_app.status == "active"
        )
