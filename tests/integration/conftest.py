# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import os

import pytest
from pytest_operator.plugin import OpsTest

from . import juju_
from . import architecture
from .helpers import APPLICATION_DEFAULT_APP_NAME, get_application_name

logger = logging.getLogger(__name__)

@pytest.fixture
def ubuntu_base():
    return os.environ["CHARM_UBUNTU_BASE"]

@pytest.fixture
def charm(ubuntu_base):
    # Return str instead of pathlib.Path since python-libjuju's model.deploy(), juju deploy, and
    # juju bundle files expect local charms to begin with `./` or `/` to distinguish them from
    # Charmhub charms.
    return f"./mysql-router_ubuntu@{ubuntu_base}-{architecture.architecture}.charm"

@pytest.fixture
async def continuous_writes(ops_test: OpsTest):
    """Starts continuous writes to the MySQL cluster for a test and clear the writes at the end."""
    application_name = get_application_name(ops_test, APPLICATION_DEFAULT_APP_NAME)

    application_unit = ops_test.model.applications[application_name].units[0]

    logger.info("Clearing continuous writes")
    await juju_.run_action(application_unit, "clear-continuous-writes")

    logger.info("Starting continuous writes")
    await juju_.run_action(application_unit, "start-continuous-writes")

    yield

    logger.info("Clearing continuous writes")
    await juju_.run_action(application_unit, "clear-continuous-writes")
