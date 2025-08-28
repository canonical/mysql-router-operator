#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging
import subprocess
import typing

import pytest
import tenacity
from pytest_operator.plugin import OpsTest

from . import architecture, juju_
from .helpers import (
    MYSQL_DEFAULT_APP_NAME,
    MYSQL_ROUTER_DEFAULT_APP_NAME,
    execute_queries_against_unit,
    get_data_integrator_credentials,
    get_juju_status,
    get_machine_address,
    get_tls_certificate_issuer,
)

logger = logging.getLogger(__name__)


MYSQL_APP_NAME = MYSQL_DEFAULT_APP_NAME
MYSQL_ROUTER_APP_NAME = MYSQL_ROUTER_DEFAULT_APP_NAME
DATA_INTEGRATOR_APP_NAME = "data-integrator"
HA_CLUSTER_APP_NAME = "hacluster"
TIMEOUT = 20 * 60
SMALL_TIMEOUT = 5 * 60
TEST_DATABASE = "testdatabase"

if juju_.is_3_or_higher:
    tls_app_name = "self-signed-certificates"
    tls_channel = "latest/edge" if architecture.architecture == "arm64" else "latest/stable"
    tls_config = {"ca-common-name": "Test CA"}
else:
    tls_app_name = "tls-certificates-operator"
    tls_channel = "legacy/edge" if architecture.architecture == "arm64" else "legacy/stable"
    tls_config = {"generate-self-signed-certificates": "true", "ca-common-name": "Test CA"}

vip = None


async def ensure_database_accessible_from_vip(
    ops_test: OpsTest, avoid_unit: typing.Optional[str] = None
) -> None:
    """Ensure that the database is access from the VIP."""
    logger.info("Ensure database accessible via VIP")
    credentials = await get_data_integrator_credentials(
        ops_test, DATA_INTEGRATOR_APP_NAME, avoid_unit=avoid_unit
    )
    hostname = credentials["endpoints"].split(",")[0].split(":")[0]
    global vip
    assert hostname == vip, "An endpoint hostname other than VIP returned"

    databases = await execute_queries_against_unit(
        hostname,
        credentials["username"],
        credentials["password"],
        ["SHOW DATABASES;"],
        port=credentials["endpoints"].split(",")[0].split(":")[1],
    )
    assert TEST_DATABASE in databases, "Test database not externally accessible through VIP"


async def generate_next_available_ip(
    ops_test: OpsTest, starting_ip: str, exclude_ips: list[str] = []
) -> str:
    """Compute and return the next available IP in the model's subnet."""
    all_ip_addresses = [
        await get_machine_address(ops_test, unit) for unit in ops_test.model.units.values()
    ]

    base, last_octet = starting_ip.rsplit(".", 1)
    last_octet = int(last_octet)
    for _ in range(len(all_ip_addresses)):
        last_octet += 1
        if last_octet > 254:
            last_octet = 2
        addr = ".".join([base, str(last_octet)])
        if addr not in all_ip_addresses and addr not in exclude_ips:
            return addr

    assert False, "Unable to compute next available IP"


@pytest.mark.abort_on_fail
async def test_external_connectivity_vip_with_hacluster(ops_test: OpsTest, charm, series) -> None:
    """Test external connectivity and VIP with data-integrator hacluster."""
    logger.info("Deploy and relate all applications without hacluster")
    # speed up test by firing update-status more frequently (for hacluster)
    async with ops_test.fast_forward("60s"):
        # deploy data-integrator with mysqlrouter
        _, _, data_integrator_application = await asyncio.gather(
            ops_test.model.deploy(
                MYSQL_APP_NAME,
                channel="8.0/edge",
                config={"profile": "testing"},
                num_units=1,
            ),
            ops_test.model.deploy(
                charm,
                application_name=MYSQL_ROUTER_APP_NAME,
                num_units=None,
                series=series,
            ),
            ops_test.model.deploy(
                DATA_INTEGRATOR_APP_NAME,
                application_name=DATA_INTEGRATOR_APP_NAME,
                channel="latest/stable",
                series=series,
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
            await get_machine_address(ops_test, unit) for unit in data_integrator_application.units
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
        await ops_test.model.relate(f"{MYSQL_ROUTER_APP_NAME}:ha", f"{HA_CLUSTER_APP_NAME}:ha")

        logger.info("Configure the VIP on mysqlrouter")
        global vip
        vip = await generate_next_available_ip(ops_test, hostname)

        await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].set_config({"vip": vip})

        for attempt in tenacity.Retrying(
            reraise=True,
            stop=tenacity.stop_after_delay(TIMEOUT),
            wait=tenacity.wait_fixed(10),
        ):
            with attempt:
                credentials = await get_data_integrator_credentials(
                    ops_test, DATA_INTEGRATOR_APP_NAME
                )
                hostname = credentials["endpoints"].split(",")[0].split(":")[0]
                assert hostname == vip, "Configured VIP not in effect"

        await ops_test.model.wait_for_idle(status="active", timeout=TIMEOUT)

        await ensure_database_accessible_from_vip(ops_test)

        logger.info("Reconfiguring the VIP")
        vip = await generate_next_available_ip(ops_test, vip, exclude_ips=[vip])

        await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].set_config({"vip": vip})

        for attempt in tenacity.Retrying(
            reraise=True,
            stop=tenacity.stop_after_delay(TIMEOUT),
            wait=tenacity.wait_fixed(10),
        ):
            with attempt:
                credentials = await get_data_integrator_credentials(
                    ops_test, DATA_INTEGRATOR_APP_NAME
                )
                hostname = credentials["endpoints"].split(",")[0].split(":")[0]
                assert hostname == vip, "Reconfigured VIP not in effect"

        await ops_test.model.wait_for_idle(status="active", timeout=TIMEOUT)

        logger.info("Ensure database accessible via reconfigured VIP")
        await ensure_database_accessible_from_vip(ops_test)


@pytest.mark.abort_on_fail
async def test_hacluster_failover(ops_test: OpsTest) -> None:
    """Test the failover of the hacluster leader."""
    logger.info("Stopping the lxd container for the hacluster primary")
    hacluster_leader_unit = None
    for unit in ops_test.model.applications[HA_CLUSTER_APP_NAME].units:
        if await unit.is_leader_from_status():
            hacluster_leader_unit = unit
            break

    subprocess.check_output(
        ["lxc", "stop", hacluster_leader_unit.machine.hostname], encoding="utf-8"
    )

    logger.info("Waiting till machine is stopped")
    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            assert "unknown" in get_juju_status(ops_test.model.name), (
                "Stopped machine's workload status not unknown"
            )

    await ops_test.model.wait_for_idle(status="active", timeout=TIMEOUT)

    logger.info("Ensuring database still accessible via VIP")
    avoid_unit = hacluster_leader_unit.principal_unit
    await ensure_database_accessible_from_vip(ops_test, avoid_unit=avoid_unit)

    logger.info("Starting stopped machine")
    subprocess.check_output(
        ["lxc", "start", hacluster_leader_unit.machine.hostname], encoding="utf-8"
    )

    logger.info("Waiting till machine is started")
    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            assert "unknown" not in get_juju_status(ops_test.model.name), (
                "Started machine's workload status is unknown"
            )

    await ops_test.model.wait_for_idle(status="active", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_tls_along_with_ha_cluster(ops_test: OpsTest, series) -> None:
    """Ensure that mysqlrouter is externally accessible with TLS integration."""
    logger.info("Deploying TLS")
    async with ops_test.fast_forward("60s"):
        await ops_test.model.deploy(
            tls_app_name,
            application_name=tls_app_name,
            channel=tls_channel,
            config=tls_config,
        )

    logger.info("Ensure auto-generated TLS cert before relation with TLS")
    mysqlrouter_unit = ops_test.model.applications[MYSQL_ROUTER_APP_NAME].units[0]
    credentials = await get_data_integrator_credentials(ops_test, DATA_INTEGRATOR_APP_NAME)
    [database_host, database_port] = credentials["endpoints"].split(",")[0].split(":")
    issuer = await get_tls_certificate_issuer(
        ops_test,
        mysqlrouter_unit.name,
        host=database_host,
        port=database_port,
    )
    assert "Issuer: CN = MySQL_Router_Auto_Generated_CA_Certificate" in issuer, (
        "Expected mysqlrouter autogenerated certificate"
    )

    logger.info("Ensure router externally accessible before TLS integration")
    await ensure_database_accessible_from_vip(ops_test)

    logger.info("Relate TLS with MySQLRouter")
    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:certificates", f"{tls_app_name}:certificates"
    )

    await ops_test.model.wait_for_idle([tls_app_name], status="active", timeout=TIMEOUT)

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            issuer = await get_tls_certificate_issuer(
                ops_test,
                mysqlrouter_unit.name,
                host=database_host,
                port=database_port,
            )
            assert "CN = Test CA" in issuer, (
                f"Expected mysqlrouter certificate from {tls_app_name}"
            )

    logger.info("Ensure router externally accessible after TLS integration")
    await ensure_database_accessible_from_vip(ops_test)

    logger.info(f"Removing relation between mysqlrouter and {tls_app_name}")
    await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].remove_relation(
        f"{MYSQL_ROUTER_APP_NAME}:certificates", f"{tls_app_name}:certificates"
    )

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            issuer = await get_tls_certificate_issuer(
                ops_test,
                mysqlrouter_unit.name,
                host=database_host,
                port=database_port,
            )
            assert "Issuer: CN = MySQL_Router_Auto_Generated_CA_Certificate" in issuer, (
                "Expected mysqlrouter autogenerated certificate"
            )

    logger.info("Ensure router externally accessible after TLS integration removed")
    await ensure_database_accessible_from_vip(ops_test)


@pytest.mark.abort_on_fail
async def test_remove_vip(ops_test: OpsTest) -> None:
    """Ensure removal of VIP results in connection through data-integrator."""
    async with ops_test.fast_forward("60s"):
        logger.info("Resetting the VIP")
        await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].reset_config(["vip"])
        await ops_test.model.block_until(
            lambda: ops_test.model.applications[MYSQL_ROUTER_APP_NAME].units[0].workload_status
            == "blocked",
            timeout=300,
        )
        assert (
            ops_test.model.applications[MYSQL_ROUTER_APP_NAME].units[0].workload_status_message
            == "ha integration used without vip configuration"
        ), "Incorrect mysql router unit status message"

        logger.info("Removing the relation between hacluster and mysqlrouter")
        await ops_test.model.applications[MYSQL_ROUTER_APP_NAME].remove_relation(
            f"{MYSQL_ROUTER_APP_NAME}:ha", f"{HA_CLUSTER_APP_NAME}:ha"
        )
        await ops_test.model.wait_for_idle(
            [MYSQL_ROUTER_APP_NAME], status="active", timeout=TIMEOUT
        )

    logger.info("Ensuring that VIP is not the data-integrator endpoint hostname")
    credentials = await get_data_integrator_credentials(ops_test, DATA_INTEGRATOR_APP_NAME)
    hostname = credentials["endpoints"].split(",")[0].split(":")[0]
    logger.info(f"Data integrator endpoint hostname is {hostname}")
    assert hostname != vip, "Hostname is VIP"
