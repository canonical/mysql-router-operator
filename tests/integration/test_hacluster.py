#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from pytest_operator.plugin import OpsTest

from .helpers import (
    MYSQL_DEFAULT_APP_NAME,
    MYSQL_ROUTER_DEFAULT_APP_NAME,
    execute_queries_against_unit,
    get_data_integrator_credentials,
    get_machine_address,
)

logger = logging.getLogger(__name__)


MYSQL_APP_NAME = MYSQL_DEFAULT_APP_NAME
MYSQL_ROUTER_APP_NAME = MYSQL_ROUTER_DEFAULT_APP_NAME
DATA_INTEGRATOR_APP_NAME = "data-integrator"
HA_CLUSTER_APP_NAME = "hacluster"
TIMEOUT = 15 * 60
TEST_DATABASE = "testdatabase"


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_external_connectivity_vip_with_hacluster(
    ops_test: OpsTest, mysql_router_charm_series
) -> None:
    """Test external connectivity and VIP with data-integrator hacluster."""
    logger.info("Deploy and relate all applications without hacluster")
    async with ops_test.fast_forward():
        # deploy mysql first
        await ops_test.model.deploy(
            MYSQL_APP_NAME,
            channel="8.0/edge",
            config={"profile": "testing"},
            num_units=1,
        )

        # mysqlrouter charm
        mysqlrouter_charm = await ops_test.build_charm(".")

        # deploy data-integrator with mysqlrouter
        _, data_integrator_application = await asyncio.gather(
            ops_test.model.deploy(
                mysqlrouter_charm,
                application_name=MYSQL_ROUTER_APP_NAME,
                num_units=None,
                series=mysql_router_charm_series,
            ),
            ops_test.model.deploy(
                DATA_INTEGRATOR_APP_NAME,
                application_name=DATA_INTEGRATOR_APP_NAME,
                channel="latest/stable",
                series=mysql_router_charm_series,
                config={"database-name": TEST_DATABASE},
                num_units=4,
            ),
        )

        await ops_test.model.relate(
            f"{MYSQL_ROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
        )
        await ops_test.model.relate(
            f"{DATA_INTEGRATOR_APP_NAME}:mysql", f"{MYSQL_ROUTER_APP_NAME}:database"
        )

        logger.info("Waiting for applications to become active")
        # We can safely wait only for data-integrator to be ready,
        # given that it will only become active once all the other
        # applications are ready.
        await ops_test.model.wait_for_idle(
            [DATA_INTEGRATOR_APP_NAME], status="active", timeout=TIMEOUT
        )

        logger.info("Ensure the database is accessible externally")
        credentials = await get_data_integrator_credentials(ops_test, DATA_INTEGRATOR_APP_NAME)
        hostname = credentials["endpoints"].split(",")[0].split(":")[0]
        databases = await execute_queries_against_unit(
            hostname,
            credentials["username"],
            credentials["password"],
            ["SHOW DATABASES;"],
            port=credentials["endpoints"].split(",")[0].split(":")[1],
        )
        assert TEST_DATABASE in databases, "Test database not externally accessible"

        logger.info("Ensure provided host in a data-integrator ip")
        data_integrator_ips = [
            await get_machine_address(unit) for unit in data_integrator_application.units
        ]
        assert hostname in data_integrator_ips, "Hostname is not a data-integrator"

        logger.info("Deploy and relate hacluster")
        await ops_test.model.deploy(
            HA_CLUSTER_APP_NAME,
            channel="2.4/stable",
        )

        await ops_test.model.relate(
            f"{DATA_INTEGRATOR_APP_NAME}:juju-info", f"{HA_CLUSTER_APP_NAME}:juju-info"
        )
        await ops_test.model.relate(
            f"{MYSQL_ROUTER_APP_NAME}:hacluster", f"{HA_CLUSTER_APP_NAME}:ha"
        )

        await asyncio.gather(
            await ops_test.model.wait_for_idle(
                [DATA_INTEGRATOR_APP_NAME, HA_CLUSTER_APP_NAME],
                status="active",
                timeout=TIMEOUT,
            ),
            await ops_test.model.wait_for_idle(
                [MYSQL_ROUTER_APP_NAME], status="blocked", timeout=TIMEOUT
            ),
        )

        logger.info("Configure the VIP on mysqlrouter")
        all_ip_addresses = [
            await get_machine_address(ops_test, unit) for unit in ops_test.model.units
        ]

        base, last_octet = hostname[0].rsplit(".", 1)
        last_octet = int(last_octet)
        global vip
        vip = None
        for _ in range(len(all_ip_addresses)):
            last_octet += 1
            if last_octet > 254:
                last_octet = 2
            addr = ".".join([base, str(last_octet)])
            if addr not in all_ip_addresses:
                vip = addr
                break

        await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].set_config({"vip": vip})
        await ops_test.model.wait_for_idle(status="active", timeout=TIMEOUT)

        logger.info("Ensure database accessible via VIP")
        credentials = await get_data_integrator_credentials(ops_test, DATA_INTEGRATOR_APP_NAME)
        hostname = credentials["endpoints"].split(",")[0].split(":")[0]
        assert hostname == vip, "An endpoint hostname other than VIP returned"

        databases = await execute_queries_against_unit(
            hostname,
            credentials["username"],
            credentials["password"],
            ["SHOW DATABASES;"],
            port=credentials["endpoints"].split(",")[0].split(":")[1],
        )
        assert TEST_DATABASE in databases, "Test database not externally accessible through VIP"

        logger.info("Reconfiguring the VIP")
        base, last_octet = vip.rsplit(".", 1)
        last_octet = int(last_octet)
        for _ in range(len(all_ip_addresses)):
            last_octet += 1
            if last_octet > 254:
                last_octet = 2
            addr = ".".join([base, str(last_octet)])
            if addr not in all_ip_addresses:
                vip = addr
                break

        await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].set_config({"vip": vip})
        await ops_test.model.wait_for_idle(status="active", timeout=TIMEOUT)

        logger.info("Ensure database accessible via reconfigured VIP")
        credentials = await get_data_integrator_credentials(ops_test, DATA_INTEGRATOR_APP_NAME)
        hostname = credentials["endpoints"].split(",")[0].split(":")[0]
        assert hostname == vip, "An endpoint hostname other than reconfigured VIP returned"

        databases = await execute_queries_against_unit(
            hostname,
            credentials["username"],
            credentials["password"],
            ["SHOW DATABASES;"],
            port=credentials["endpoints"].split(",")[0].split(":")[1],
        )
        assert (
            TEST_DATABASE in databases
        ), "Test database not externally accessible through reconfigured VIP"
