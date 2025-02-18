# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
import tenacity
from pytest_operator.plugin import OpsTest

from . import architecture, juju_
from .helpers import (
    APPLICATION_DEFAULT_APP_NAME,
    MYSQL_DEFAULT_APP_NAME,
    MYSQL_ROUTER_DEFAULT_APP_NAME,
    get_tls_certificate_issuer,
)

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = MYSQL_DEFAULT_APP_NAME
MYSQL_ROUTER_APP_NAME = MYSQL_ROUTER_DEFAULT_APP_NAME
TEST_APP_NAME = APPLICATION_DEFAULT_APP_NAME
SLOW_TIMEOUT = 15 * 60
RETRY_TIMEOUT = 60

if juju_.is_3_or_higher:
    tls_app_name = "self-signed-certificates"
    tls_channel = "latest/edge" if architecture.architecture == "arm64" else "latest/stable"
    tls_config = {"ca-common-name": "Test CA"}
else:
    tls_app_name = "tls-certificates-operator"
    tls_channel = "legacy/edge" if architecture.architecture == "arm64" else "legacy/stable"
    tls_config = {"generate-self-signed-certificates": "true", "ca-common-name": "Test CA"}


@pytest.mark.abort_on_fail
async def test_build_deploy_and_relate(ops_test: OpsTest, charm, series) -> None:
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

        # tls, test app and router
        await asyncio.gather(
            ops_test.model.deploy(
                charm,
                application_name=MYSQL_ROUTER_APP_NAME,
                num_units=None,
                series=series,
            ),
            ops_test.model.deploy(
                tls_app_name,
                application_name=tls_app_name,
                channel=tls_channel,
                config=tls_config,
                series="jammy",
            ),
            ops_test.model.deploy(
                TEST_APP_NAME,
                application_name=TEST_APP_NAME,
                channel="latest/edge",
                series=series,
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


@pytest.mark.abort_on_fail
async def test_connected_encryption(ops_test: OpsTest) -> None:
    """Test encryption when backend database is using TLS."""
    mysqlrouter_unit = ops_test.model.applications[MYSQL_ROUTER_APP_NAME].units[0]

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
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
    await ops_test.model.relate(tls_app_name, MYSQL_ROUTER_APP_NAME)

    logger.info("Getting certificate issuer after relating with tls operator")
    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
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
            ), f"Expected mysqlrouter certificate from {tls_app_name}"

    logger.info("Removing relation TLS with mysqlrouter")
    await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].remove_relation(
        f"{tls_app_name}:certificates", f"{MYSQL_ROUTER_APP_NAME}:certificates"
    )

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
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
