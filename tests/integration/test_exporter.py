#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
import tenacity
import urllib3
from pytest_operator.plugin import OpsTest

from . import juju_
from .helpers import (
    APPLICATION_DEFAULT_APP_NAME,
    MYSQL_DEFAULT_APP_NAME,
    MYSQL_ROUTER_DEFAULT_APP_NAME,
    get_tls_certificate_issuer,
)

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = MYSQL_DEFAULT_APP_NAME
MYSQL_ROUTER_APP_NAME = MYSQL_ROUTER_DEFAULT_APP_NAME
APPLICATION_APP_NAME = APPLICATION_DEFAULT_APP_NAME
GRAFANA_AGENT_APP_NAME = "grafana-agent"
SLOW_TIMEOUT = 25 * 60
RETRY_TIMEOUT = 3 * 60

if juju_.is_3_or_higher:
    TLS_APP_NAME = "self-signed-certificates"
    TLS_CONFIG = {"ca-common-name": "Test CA"}
else:
    TLS_APP_NAME = "tls-certificates-operator"
    TLS_CONFIG = {"generate-self-signed-certificates": "true", "ca-common-name": "Test CA"}


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_exporter_endpoint(ops_test: OpsTest, mysql_router_charm_series: str) -> None:
    """Test that exporter endpoint is functional."""
    http = urllib3.PoolManager()

    # Build and deploy applications
    mysqlrouter_charm = await ops_test.build_charm(".")

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
            mysqlrouter_charm,
            application_name=MYSQL_ROUTER_APP_NAME,
            num_units=0,
            series=mysql_router_charm_series,
        ),
        ops_test.model.deploy(
            APPLICATION_APP_NAME,
            application_name=APPLICATION_APP_NAME,
            num_units=1,
            # MySQL Router and Grafana agent are subordinate -
            # they will use the series of the principal charm
            series=mysql_router_charm_series,
            channel="latest/edge",
        ),
        ops_test.model.deploy(
            GRAFANA_AGENT_APP_NAME,
            application_name=GRAFANA_AGENT_APP_NAME,
            num_units=0,
            channel="latest/stable",
            series=mysql_router_charm_series,
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
        http.request("GET", f"http://{unit_address}:49152/metrics")
    except urllib3.exceptions.MaxRetryError as e:
        assert (
            "[Errno 111] Connection refused" in e.reason.args[0]
        ), "❌ expected connection refused error"
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
            jmx_resp = http.request("GET", f"http://{unit_address}:49152/metrics")
            assert (
                jmx_resp.status == 200
            ), "❌ cannot connect to metrics endpoint with relation with cos"
            assert "mysqlrouter_route_health" in str(
                jmx_resp.data
            ), "❌ did not find expected metric in response"

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
                http.request("GET", f"http://{unit_address}:49152/metrics")
            except urllib3.exceptions.MaxRetryError as e:
                assert (
                    "[Errno 111] Connection refused" in e.reason.args[0]
                ), "❌ expected connection refused error"
            else:
                assert False, "❌ can connect to metrics endpoint without relation with cos"


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_exporter_endpoint_with_tls(ops_test: OpsTest) -> None:
    """Test that the exporter endpoint works when related with TLS"""
    http = urllib3.PoolManager()

    mysql_router_app = ops_test.model.applications[MYSQL_ROUTER_APP_NAME]
    mysql_router_unit = mysql_router_app.units[0]

    issuer = await get_tls_certificate_issuer(
        ops_test,
        mysql_router_unit.name,
        socket="/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
    )
    assert (
        "Issuer: CN = MySQL_Router_Auto_Generated_CA_Certificate" in issuer
    ), "Expected mysqlrouter autogenerated certificate"

    logger.info(f"Deploying {TLS_APP_NAME}")
    await ops_test.model.deploy(
        TLS_APP_NAME,
        application_name=TLS_APP_NAME,
        channel="stable",
        config=TLS_CONFIG,
        series="jammy",
    )
    await ops_test.model.wait_for_idle([TLS_APP_NAME], status="active", timeout=SLOW_TIMEOUT)

    logger.info(f"Relating mysqlrouter with {TLS_APP_NAME}")

    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:certificates", f"{TLS_APP_NAME}:certificates"
    )

    mysql_test_app = ops_test.model.applications[APPLICATION_APP_NAME]
    unit_address = await mysql_test_app.units[0].get_public_address()

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            try:
                http.request("GET", f"http://{unit_address}:49152/metrics")
            except urllib3.exceptions.MaxRetryError as e:
                assert (
                    "[Errno 111] Connection refused" in e.reason.args[0]
                ), "❌ expected connection refused error"
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
            jmx_resp = http.request("GET", f"http://{unit_address}:49152/metrics")
            assert (
                jmx_resp.status == 200
            ), "❌ cannot connect to metrics endpoint with relation with cos"
            assert "mysqlrouter_route_health" in str(
                jmx_resp.data
            ), "❌ did not find expected metric in response"

    issuer = await get_tls_certificate_issuer(
        ops_test,
        mysql_router_unit.name,
        socket="/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
    )
    assert "CN = Test CA" in issuer, f"Expected mysqlrouter certificate from {TLS_APP_NAME}"

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
                http.request("GET", f"http://{unit_address}:49152/metrics")
            except urllib3.exceptions.MaxRetryError as e:
                assert (
                    "[Errno 111] Connection refused" in e.reason.args[0]
                ), "❌ expected connection refused error"
            else:
                assert False, "❌ can connect to metrics endpoint without relation with cos"

    logger.info(f"Removing relation between mysqlrouter and {TLS_APP_NAME}")
    await mysql_router_app.remove_relation(
        f"{MYSQL_ROUTER_APP_NAME}:certificates", f"{TLS_APP_NAME}:certificates"
    )

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            issuer = await get_tls_certificate_issuer(
                ops_test,
                mysql_router_unit.name,
                socket="/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
            )
            assert (
                "Issuer: CN = MySQL_Router_Auto_Generated_CA_Certificate" in issuer
            ), "Expected mysqlrouter autogenerated certificate"
