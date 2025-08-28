# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging
import os
import pathlib
import shutil
import typing
import zipfile

import pytest
import tomli
import tomli_w
from pytest_operator.plugin import OpsTest

from .helpers import (
    APPLICATION_DEFAULT_APP_NAME,
    MYSQL_DEFAULT_APP_NAME,
    MYSQL_ROUTER_DEFAULT_APP_NAME,
    ensure_all_units_continuous_writes_incrementing,
)
from .juju_ import run_action

logger = logging.getLogger(__name__)

TIMEOUT = 20 * 60
UPGRADE_TIMEOUT = 15 * 60
SMALL_TIMEOUT = 5 * 60

MYSQL_APP_NAME = MYSQL_DEFAULT_APP_NAME
MYSQL_ROUTER_APP_NAME = MYSQL_ROUTER_DEFAULT_APP_NAME
TEST_APP_NAME = APPLICATION_DEFAULT_APP_NAME


@pytest.mark.abort_on_fail
async def test_deploy_edge(ops_test: OpsTest, series) -> None:
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
            series=series,
        ),
        ops_test.model.deploy(
            TEST_APP_NAME,
            application_name=TEST_APP_NAME,
            num_units=3,
            channel="latest/edge",
            series=series,
        ),
    )

    logger.info(f"Relating {MYSQL_ROUTER_APP_NAME} to {MYSQL_APP_NAME} and {TEST_APP_NAME}")

    await ops_test.model.relate(
        f"{MYSQL_ROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
    )
    await ops_test.model.relate(f"{TEST_APP_NAME}:database", f"{MYSQL_ROUTER_APP_NAME}:database")

    logger.info("Waiting for applications to become active")
    await ops_test.model.wait_for_idle(
        [MYSQL_APP_NAME, MYSQL_ROUTER_APP_NAME, TEST_APP_NAME], status="active", timeout=TIMEOUT
    )


@pytest.mark.abort_on_fail
async def test_upgrade_from_edge(ops_test: OpsTest, charm, continuous_writes) -> None:
    """Upgrade mysqlrouter while ensuring continuous writes incrementing."""
    await ensure_all_units_continuous_writes_incrementing(ops_test)

    mysql_router_application = ops_test.model.applications[MYSQL_ROUTER_APP_NAME]

    logger.info("Build charm locally")
    global temporary_charm
    temporary_charm = "./upgrade.charm"
    shutil.copy(charm, temporary_charm)

    logger.info("Update workload version and snap revision in the charm")
    create_valid_upgrade_charm(temporary_charm)

    logger.info("Refresh the charm")
    await mysql_router_application.refresh(path=temporary_charm)

    # Refresh will always be incompatible since we are downgrading the workload
    # Refresh will additionally be incompatible on PR CI (not edge CI) since unrelease charm
    # versions are always marked as incompatible
    logger.info("Wait for refresh to block as incompatible")
    await ops_test.model.block_until(
        lambda: mysql_router_application.status == "blocked", timeout=TIMEOUT
    )
    assert "incompatible" in mysql_router_application.status_message, (
        "mysql router application status not indicating that refresh incompatible"
    )

    # Highest to lowest unit number
    refresh_order = sorted(
        mysql_router_application.units,
        key=lambda unit: int(unit.name.split("/")[1]),
        reverse=True,
    )

    logger.info("Running force-refresh-start action with check-compatibility=false")
    await run_action(refresh_order[0], "force-refresh-start", **{"check-compatibility": False})

    logger.info("Wait for app status to update")
    await ops_test.model.wait_for_idle(
        [MYSQL_ROUTER_APP_NAME],
        idle_period=30,
        timeout=TIMEOUT,
    )

    logger.info("Wait for refresh to start")
    await ops_test.model.block_until(
        lambda: mysql_router_application.status == "blocked", timeout=3 * 60
    )
    assert "resume-refresh" in mysql_router_application.status_message, (
        "mysql router application status not indicating that user should resume refresh"
    )

    logger.info("Wait for first unit to upgrade")
    async with ops_test.fast_forward("60s"):
        await ops_test.model.wait_for_idle(
            [MYSQL_ROUTER_APP_NAME],
            idle_period=30,
            timeout=TIMEOUT,
        )

    logger.info("Running resume-refresh")
    await run_action(refresh_order[1], "resume-refresh")

    logger.info("Waiting for upgrade to complete on all units")
    await ops_test.model.wait_for_idle(
        [MYSQL_ROUTER_APP_NAME],
        status="active",
        idle_period=30,
        timeout=UPGRADE_TIMEOUT,
    )

    await ensure_all_units_continuous_writes_incrementing(ops_test)

    await ops_test.model.wait_for_idle(
        [MYSQL_ROUTER_APP_NAME], idle_period=30, status="active", timeout=TIMEOUT
    )


@pytest.mark.abort_on_fail
async def test_fail_and_rollback(ops_test: OpsTest, charm, continuous_writes) -> None:
    """Upgrade to an invalid version and test rollback.

    Relies on the charm built in the previous test (test_upgrade_from_edge).
    Furthermore, the previous test will refresh the charm till revision 102.
    This test will refresh the charm till the revision in src/snap.py, thus avoiding
    no-ops.
    """
    await ensure_all_units_continuous_writes_incrementing(ops_test)

    mysql_router_application = ops_test.model.applications[MYSQL_ROUTER_APP_NAME]

    fault_charm = "./faulty.charm"
    shutil.copy(charm, fault_charm)

    logger.info("Creating invalid upgrade charm")
    create_invalid_upgrade_charm(fault_charm)

    logger.info("Refreshing mysql router with an invalid charm")
    await mysql_router_application.refresh(path=fault_charm)

    logger.info("Wait for upgrade to fail")
    await ops_test.model.block_until(
        lambda: mysql_router_application.status == "blocked", timeout=TIMEOUT
    )
    assert "incompatible" in mysql_router_application.status_message, (
        "mysql router application status not indicating faulty charm incompatible"
    )

    logger.info("Ensure continuous writes while in failure state")
    await ensure_all_units_continuous_writes_incrementing(ops_test)

    logger.info("Re-refresh the charm")
    await mysql_router_application.refresh(path="./upgrade.charm")

    logger.info("Wait for the charm to be rolled back")
    await ops_test.model.wait_for_idle(
        apps=[MYSQL_ROUTER_APP_NAME], status="active", timeout=TIMEOUT, idle_period=30
    )

    logger.info("Ensure continuous writes after rollback procedure")
    await ensure_all_units_continuous_writes_incrementing(ops_test)

    os.remove(fault_charm)
    os.remove(temporary_charm)


def create_valid_upgrade_charm(charm_file: typing.Union[str, pathlib.Path]) -> None:
    """Create a valid mysql router charm for upgrade.

    Upgrades require a new snap revision to avoid no-oping.
    """
    with zipfile.ZipFile(charm_file, mode="r") as charm_zip:
        with zipfile.Path(charm_zip, "refresh_versions.toml").open("rb") as file:
            versions = tomli.load(file)

    # charm needs to refresh snap to be able to avoid no-op when upgrading.
    # set an old revision of the snap
    versions["snap"]["revisions"]["x86_64"] = "121"
    versions["snap"]["revisions"]["aarch64"] = "122"
    versions["workload"] = "8.0.39"

    with zipfile.ZipFile(charm_file, mode="a") as charm_zip:
        charm_zip.writestr("refresh_versions.toml", tomli_w.dumps(versions))


def create_invalid_upgrade_charm(charm_file: typing.Union[str, pathlib.Path]) -> None:
    """Create an invalid mysql router charm for upgrade."""
    with zipfile.ZipFile(charm_file, mode="r") as charm_zip:
        with zipfile.Path(charm_zip, "refresh_versions.toml").open("rb") as file:
            versions = tomli.load(file)

    versions["charm"] = "8.0/0.0.0"

    with zipfile.ZipFile(charm_file, mode="a") as charm_zip:
        # an invalid charm version because the major workload_version is one less than the current workload_version
        charm_zip.writestr("refresh_versions.toml", tomli_w.dumps(versions))
