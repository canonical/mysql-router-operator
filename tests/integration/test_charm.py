#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.


import logging
import socket
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
APP_NAME = METADATA["name"]
DEFAULT_PORT = 3600


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    # build and deploy charm from local source folder
    charm = await ops_test.build_charm(".")
    await ops_test.model.deploy(
        charm,
        application_name=APP_NAME,
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="waiting",
        raise_on_blocked=True,
        timeout=1000,
    )

    assert ops_test.model.applications[APP_NAME].units[0].workload_status == "waiting"


@pytest.mark.abort_on_fail
async def test_application_is_up(ops_test: OpsTest):
    """Test if the application is up."""
    status = await ops_test.model.get_status()  # noqa: F821
    address = status["applications"][APP_NAME]["units"][f"{APP_NAME}/0"]["address"]

    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    target = (address, DEFAULT_PORT)

    logger.info("Querying app open port at %s:%s", address, DEFAULT_PORT)
    port_status = test_socket.connect_ex(target)
    test_socket.close()

    assert port_status == 0
