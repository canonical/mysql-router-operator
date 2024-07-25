# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import os
import pathlib
from unittest.mock import PropertyMock

import pytest
import pytest_operator.plugin
from ops import JujuVersion
from pytest_mock import MockerFixture
from pytest_operator.plugin import OpsTest

from . import juju_
from .helpers import APPLICATION_DEFAULT_APP_NAME, get_application_name

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def mysql_router_charm_series(pytestconfig) -> str:
    return pytestconfig.option.mysql_router_charm_series


@pytest.fixture(scope="module")
def ops_test(
    ops_test: pytest_operator.plugin.OpsTest, pytestconfig
) -> pytest_operator.plugin.OpsTest:
    _build_charm = ops_test.build_charm

    async def build_charm(charm_path) -> pathlib.Path:
        if pathlib.Path(charm_path) == pathlib.Path("."):
            # Building mysql charm
            return await _build_charm(
                charm_path,
                bases_index=pytestconfig.option.mysql_router_charm_bases_index,
            )
        else:
            return await _build_charm(charm_path)

    ops_test.build_charm = build_charm
    return ops_test


@pytest.fixture(autouse=True)
def juju_has_secrets(mocker: MockerFixture, request):
    """This fixture will force the usage of secrets whenever run on Juju 3.x.

    NOTE: This is needed, as normally JujuVersion is set to 0.0.0 in tests
    (i.e. not the real juju version)
    """
    juju_version = os.environ["LIBJUJU_VERSION_SPECIFIER"].split("/")[0]
    if juju_version < "3":
        mocker.patch.object(
            JujuVersion, "has_secrets", new_callable=PropertyMock
        ).return_value = False
        return False
    else:
        mocker.patch.object(
            JujuVersion, "has_secrets", new_callable=PropertyMock
        ).return_value = True
        return True


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
