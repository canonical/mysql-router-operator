# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging
import os
import pathlib
import re
import shutil
import typing
import zipfile

import pytest
import tenacity
from pytest_operator.plugin import OpsTest

from .helpers import (
    APPLICATION_DEFAULT_APP_NAME,
    MYSQL_DEFAULT_APP_NAME,
    ensure_all_units_continuous_writes_incrementing,
    get_workload_version,
)

logger = logging.getLogger(__name__)

TIMEOUT = 20 * 60
RETRY_TIMEOUT = 5 * 60

MYSQL_APP_NAME = MYSQL_DEFAULT_APP_NAME
MYSQL_ROUTER_APP_NAME = "mysql-router"
TEST_APP_NAME = APPLICATION_DEFAULT_APP_NAME


@pytest.fixture()
def updated_workload_version_file():
    logger.info("Updating workload_version")

    with open("workload_version", "r+") as workload_version_file:
        old_workload_version = workload_version_file.readline().strip()
        workload_version_file.seek(0)
        workload_version_file.write(f"{old_workload_version}+testupgrade\n")
        workload_version_file.flush()

    yield

    logger.info("Restoring workload_version")

    with open("workload_version", "w") as workload_version_file:
        workload_version_file.write(f"{old_workload_version}\n")
        workload_version_file.flush()


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_deploy_latest(ops_test: OpsTest, mysql_router_charm_series: str) -> None:
    """Simple test to ensure that mysql, mysqlrouter and application charms deploy."""
    logger.info("Deploying all applications")
    await asyncio.gather(
        ops_test.model.deploy(
            MYSQL_APP_NAME,
            application_name=MYSQL_APP_NAME,
            num_units=1,
            channel="8.0/edge",
            config={"profile": "testing"},
            series="jammy",
        ),
        ops_test.model.deploy(
            MYSQL_ROUTER_APP_NAME,
            application_name=MYSQL_ROUTER_APP_NAME,
            num_units=1,
            channel="dpe/edge",
            series=mysql_router_charm_series,
        ),
        ops_test.model.deploy(
            TEST_APP_NAME,
            application_name=TEST_APP_NAME,
            num_units=1,
            channel="latest/edge",
            series=mysql_router_charm_series,
        ),
    )

    logger.info(f"Relating {MYSQL_ROUTER_APP_NAME} to {MYSQL_APP_NAME} and {TEST_APP_NAME}")

    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
    )
    await ops_test.model.relate(f"{TEST_APP_NAME}:database", f"{MYSQL_ROUTER_APP_NAME}:database")

    logger.info("Waiting for applications to become active")
    # We can safely wait only for test application to be ready, given that it will
    # only become active once all the other applications are ready.
    await ops_test.model.wait_for_idle([TEST_APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_upgrade_from_edge(
    ops_test: OpsTest, continuous_writes, updated_workload_version_file
) -> None:
    """Upgrade mysqlrouter while ensuring continuous writes incrementing."""
    await ensure_all_units_continuous_writes_incrementing(ops_test)

    mysql_router_application = ops_test.model.applications[MYSQL_ROUTER_APP_NAME]
    mysql_router_unit = mysql_router_application.units[0]

    old_workload_version = await get_workload_version(ops_test, mysql_router_unit.name)

    logger.info("Build charm locally")
    global charm
    charm = await ops_test.build_charm(".")

    logger.info("Refresh the charm")
    await mysql_router_application.refresh(path=charm)

    logger.info("Wait for upgrade to complete")
    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            workload_version = await get_workload_version(ops_test, mysql_router_unit.name)
            assert old_workload_version != workload_version

    await ops_test.model.wait_for_idle(
        apps=[MYSQL_APP_NAME], status="active", idle_period=30, timeout=TIMEOUT
    )

    await ensure_all_units_continuous_writes_incrementing(ops_test)

    await ops_test.model.wait_for_idle([MYSQL_ROUTER_APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_fail_and_rollback(ops_test) -> None:
    """Upgrade to an invalid version and test rollback."""
    await ensure_all_units_continuous_writes_incrementing(ops_test)

    mysql_router_application = ops_test.model.applications[MYSQL_ROUTER_APP_NAME]
    mysql_router_unit = mysql_router_application.units[0]

    fault_charm = f"/tmp/{charm.name}"
    shutil.copy(charm, fault_charm)

    logger.info("Injecting invalid workload_version")
    inject_invalid_workload_version(fault_charm)

    logger.info("Refreshing the charm with the invalid workload_version")
    await mysql_router_application.refresh(path=fault_charm)

    logger.info("Wait for upgrade to fail")
    await ops_test.model.block_until(
        lambda: mysql_router_application.status == "blocked", timeout=TIMEOUT
    )

    logger.info("Ensure continuous writes while in failure state")
    await ensure_all_units_continuous_writes_incrementing(ops_test)

    logger.info("Re-refresh the charm")
    await mysql_router_application.refresh(path=charm)

    for attempt in tenacity.Retrying(
        reraise=True,
        stop=tenacity.stop_after_delay(RETRY_TIMEOUT),
        wait=tenacity.wait_fixed(10),
    ):
        with attempt:
            charm_workload_version = await get_workload_version(ops_test, mysql_router_unit.name)

            with open("workload_version", "r") as workload_version_file:
                workload_version = workload_version_file.readline().strip()

            assert charm_workload_version == f"{workload_version}+testupgrade"

    await ops_test.model.wait_for_idle(
        apps=[MYSQL_ROUTER_APP_NAME], status="active", timeout=TIMEOUT
    )

    logger.info("Ensure continuous writes after rollback procedue")
    await ensure_all_units_continuous_writes_incrementing(ops_test)

    os.remove(fault_charm)


def inject_invalid_workload_version(charm_file: typing.Union[str, pathlib.Path]) -> None:
    """Inject an invalid charm_version file into the mysqlrouter charm."""
    with open("workload_version", "r") as workload_version_file:
        old_workload_version = workload_version_file.readline().strip().split("+")[0]

        [major, minor, patch] = old_workload_version.split(".")

    with zipfile.ZipFile(charm_file, mode="a") as charm_zip:
        charm_zip.writestr("workload_version", f"{int(major) - 1}.{minor}.{patch}+testupgrade\n")

        for charm_zip_info in charm_zip.infolist():
            if charm_zip_info.filename == "src/snap.py":
                with open(charm_zip_info.filename, "r+") as snap_file:
                    content = snap_file.read()
                    new_snap_content = re.sub(r'REVISION = "\d+"', 'REVISION = "98"', str(content))

        charm_zip.writestr("src/snap.py", new_snap_content)
