# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

MYSQL_APP_NAME = "mysql"
MYSQL_ROUTER_APP_NAME = "mysqlrouter"
TEST_APP_NAME = "mysql-test-app"
TLS_APP_NAME = "tls-certificates-operator"
SLOW_TIMEOUT = 15 * 60
MODEL_CONFIG = {"logging-config": "<root>=INFO;unit=DEBUG"}


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_build_deploy_and_relate(ops_test: OpsTest, mysql_router_charm_series: str) -> None:
    """Test encryption when backend database is using TLS."""
    # Deploy TLS Certificates operator.
    await ops_test.model.set_config(MODEL_CONFIG)
    logger.info("Deploy and relate all applications")
    async with ops_test.fast_forward():
        # deploy mysql first
        await ops_test.model.deploy(
            MYSQL_APP_NAME, channel="8.0/edge", config={"profile": "testing"}, num_units=3
        )
        tls_config = {"generate-self-signed-certificates": "true", "ca-common-name": "Test CA"}

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
                TLS_APP_NAME, application_name=TLS_APP_NAME, channel="stable", config=tls_config
            ),
            ops_test.model.deploy(
                TEST_APP_NAME, application_name=TEST_APP_NAME, channel="latest/edge"
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
        ops_test.model.wait_for_idle(TEST_APP_NAME, status="active", timeout=15 * 60)


@pytest.mark.group(1)
async def test_connected_encryption(ops_test: OpsTest) -> None:
    """Test encryption when backend database is using TLS."""
    test_app_unit = ops_test.model.applications[TEST_APP_NAME].units[0]

    logger.info("Relating TLS with backend database")
    await ops_test.model.relate(TLS_APP_NAME, MYSQL_APP_NAME)

    # Wait for hooks start reconfiguring app
    await ops_test.model.block_until(
        lambda: ops_test.model.applications[MYSQL_APP_NAME].status != "active", timeout=4 * 60
    )
    await ops_test.model.wait_for_idle(status="active", timeout=15 * 60)

    logger.info("Get cipher when TLS is enforced")
    action = await test_app_unit.run_action("get-session-ssl-cipher")
    result = await action.wait()

    cipher = result.results["cipher"]
    # this assertion should be true even when TLS is not related to the backend database
    # because by default mysqlrouter will use TLS, unless explicitly disabled, which we never do
    assert cipher == "TLS_AES_256_GCM_SHA384", "Cipher not set"
