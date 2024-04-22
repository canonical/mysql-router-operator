# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
import tenacity
from pytest_operator.plugin import OpsTest

from . import juju_
from .helpers import get_tls_certificate_issuer

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = "mysql"
MYSQL_ROUTER_APP_NAME = "mysqlrouter"
TEST_APP_NAME = "mysql-test-app"
SLOW_TIMEOUT = 15 * 60

if juju_.is_3_or_higher:
    TLS_APP_NAME = "self-signed-certificates"
    TLS_CONFIG = {"ca-common-name": "Test CA"}
else:
    TLS_APP_NAME = "tls-certificates-operator"
    TLS_CONFIG = {"generate-self-signed-certificates": "true", "ca-common-name": "Test CA"}


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_build_deploy_and_relate(ops_test: OpsTest, mysql_router_charm_series: str) -> None:
    """Test encryption when backend database is using TLS."""
    logger.info("Deploy and relate all applications")
    async with ops_test.fast_forward():
        # deploy mysql first
        await ops_test.model.deploy(
            MYSQL_APP_NAME,
            channel="8.0/edge",
            application_name=MYSQL_APP_NAME,
            config={"profile": "testing"},
            num_units=1,
        )

        # ROUTER
        mysqlrouter_charm = await ops_test.build_charm(".")

        # tls, test app and router
        await asyncio.gather(
            ops_test.model.deploy(
                mysqlrouter_charm,
                application_name=MYSQL_ROUTER_APP_NAME,
                num_units=None,
                series=mysql_router_charm_series,
            ),
            ops_test.model.deploy(
                TLS_APP_NAME,
                application_name=TLS_APP_NAME,
                channel="stable",
                config=TLS_CONFIG,
                series="jammy",
            ),
            ops_test.model.deploy(
                TEST_APP_NAME,
                application_name=TEST_APP_NAME,
                channel="latest/edge",
                series=mysql_router_charm_series,
            ),
        )

        await ops_test.model.relate(
            f"{MYSQL_ROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
        )
        await ops_test.model.relate(
            f"{TEST_APP_NAME}:database", f"{MYSQL_ROUTER_APP_NAME}:database"
        )

        logger.info("Waiting for applications to become active")
        # We can safely wait only for test application to be ready, given that it will
        # only become active once all the other applications are ready.
        await ops_test.model.wait_for_idle([TEST_APP_NAME], status="active", timeout=SLOW_TIMEOUT)


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_connected_encryption(ops_test: OpsTest) -> None:
    """Test encryption when backend database is using TLS."""
    mysqlrouter_unit = ops_test.model.applications[MYSQL_ROUTER_APP_NAME].units[0]

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(60),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            issuer = await get_tls_certificate_issuer(
                ops_test,
                mysqlrouter_unit.name,
                socket="/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
            )
            assert (
                "Issuer: CN = MySQL_Router_Auto_Generated_CA_Certificate" in issuer
            ), "Expected mysqlrouter autogenerated certificate"

    logger.info("Relating TLS with mysqlrouter")
    await ops_test.model.relate(TLS_APP_NAME, MYSQL_ROUTER_APP_NAME)

    logger.info("Getting certificate issuer after relating with tls operator")
    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(60),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            issuer = await get_tls_certificate_issuer(
                ops_test,
                mysqlrouter_unit.name,
                socket="/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
            )
            assert (
                "CN = Test CA" in issuer
            ), f"Expected mysqlrouter certificate from {TLS_APP_NAME}"

    logger.info("Removing relation TLS with mysqlrouter")
    await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].remove_relation(
        f"{TLS_APP_NAME}:certificates", f"{MYSQL_ROUTER_APP_NAME}:certificates"
    )

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(60),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            issuer = await get_tls_certificate_issuer(
                ops_test,
                mysqlrouter_unit.name,
                socket="/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
            )
            assert (
                "Issuer: CN = MySQL_Router_Auto_Generated_CA_Certificate" in issuer
            ), "Expected mysqlrouter autogenerated CA certificate"
