#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
import requests
import tenacity
from pytest_operator.plugin import OpsTest

from .helpers import (
    APPLICATION_DEFAULT_APP_NAME,
    MYSQL_DEFAULT_APP_NAME,
    MYSQL_ROUTER_DEFAULT_APP_NAME,
)

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = MYSQL_DEFAULT_APP_NAME
MYSQL_ROUTER_APP_NAME = MYSQL_ROUTER_DEFAULT_APP_NAME
APPLICATION_APP_NAME = APPLICATION_DEFAULT_APP_NAME
GRAFANA_AGENT_APP_NAME = "grafana-agent"
SLOW_TIMEOUT = 25 * 60
RETRY_TIMEOUT = 3 * 60


@pytest.mark.abort_on_fail
async def test_exporter_endpoint(ops_test: OpsTest, charm, series) -> None:
    """Test that exporter endpoint is functional."""
    logger.info("Deploying all the applications")

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
            num_units=0,
            series=series,
        ),
        ops_test.model.deploy(
            APPLICATION_APP_NAME,
            application_name=APPLICATION_APP_NAME,
            num_units=1,
            # MySQL Router and Grafana agent are subordinate -
            # they will use the series of the principal charm
            series=series,
            channel="latest/edge",
        ),
        ops_test.model.deploy(
            GRAFANA_AGENT_APP_NAME,
            application_name=GRAFANA_AGENT_APP_NAME,
            num_units=0,
            channel="1/stable",
            series=series,
        ),
    )

    [mysql_app, mysql_router_app, mysql_test_app, grafana_agent_app] = applications

    logger.info("Relating mysqlrouter and grafana-agent with mysql-test-app")

    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:database", f"{APPLICATION_APP_NAME}:database"
    )

    await ops_test.model.relate(
        f"{APPLICATION_APP_NAME}:juju-info", f"{GRAFANA_AGENT_APP_NAME}:juju-info"
    )

    async with ops_test.fast_forward():
        await asyncio.gather(
            ops_test.model.block_until(lambda: mysql_app.status == "active", timeout=SLOW_TIMEOUT),
            ops_test.model.block_until(
                lambda: mysql_router_app.status == "blocked", timeout=SLOW_TIMEOUT
            ),
            ops_test.model.block_until(
                lambda: mysql_test_app.status == "waiting", timeout=SLOW_TIMEOUT
            ),
            ops_test.model.block_until(
                lambda: grafana_agent_app.status == "blocked", timeout=SLOW_TIMEOUT
            ),
        )

        logger.info("Relating mysqlrouter with mysql")

        await ops_test.model.relate(
            f"{MYSQL_ROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
        )

        await asyncio.gather(
            ops_test.model.block_until(lambda: mysql_app.status == "active", timeout=SLOW_TIMEOUT),
            ops_test.model.block_until(
                lambda: mysql_router_app.status == "active", timeout=SLOW_TIMEOUT
            ),
            ops_test.model.block_until(
                lambda: mysql_test_app.status == "active", timeout=SLOW_TIMEOUT
            ),
            ops_test.model.block_until(
                lambda: grafana_agent_app.status == "blocked", timeout=SLOW_TIMEOUT
            ),
        )

    unit = mysql_test_app.units[0]
    unit_address = await unit.get_public_address()

    try:
        requests.get(f"http://{unit_address}:9152/metrics", stream=False)
    except requests.exceptions.ConnectionError as e:
        assert "[Errno 111] Connection refused" in str(e), "❌ expected connection refused error"
    else:
        assert False, "❌ can connect to metrics endpoint without relation with cos"

    logger.info("Relating mysqlrouter with grafana agent")
    await ops_test.model.relate(
        f"{GRAFANA_AGENT_APP_NAME}:cos-agent", f"{MYSQL_ROUTER_APP_NAME}:cos-agent"
    )

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            response = requests.get(f"http://{unit_address}:9152/metrics", stream=False)
            response.raise_for_status()
            assert "mysqlrouter_route_health" in response.text, (
                "❌ did not find expected metric in response"
            )
            response.close()

    logger.info("Removing relation between mysqlrouter and grafana agent")
    await mysql_router_app.remove_relation(
        f"{GRAFANA_AGENT_APP_NAME}:cos-agent", f"{MYSQL_ROUTER_APP_NAME}:cos-agent"
    )

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            try:
                requests.get(f"http://{unit_address}:9152/metrics", stream=False)
            except requests.exceptions.ConnectionError as e:
                assert "[Errno 111] Connection refused" in str(e), (
                    "❌ expected connection refused error"
                )
            else:
                assert False, "❌ can connect to metrics endpoint without relation with cos"
