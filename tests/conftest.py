# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import argparse
import subprocess

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--mysql-router-charm-series", help="Ubuntu series for mysql router charm (e.g. jammy)"
    )
    parser.addoption(
        "--mysql-router-charm-bases-index",
        type=int,
        help="Index of charmcraft.yaml base that matches --mysql-router-charm-series",
    )


def pytest_configure(config):
    if (config.option.mysql_router_charm_series is None) ^ (
        config.option.mysql_router_charm_bases_index is None
    ):
        raise argparse.ArgumentError(
            None,
            "--mysql-router-charm-series and --mysql-router-charm-bases-index must be given together",
        )
    # Note: Update defaults whenever charmcraft.yaml is changed
    if config.option.mysql_router_charm_series is None:
        config.option.mysql_router_charm_series = "jammy"
    if config.option.mysql_router_charm_bases_index is None:
        config.option.mysql_router_charm_bases_index = 1


@pytest.fixture(autouse=True)
def architecture() -> str:
    return subprocess.run(
        ["dpkg", "--print-architecture"],
        capture_output=True,
        check=True,
        encoding="utf-8",
    ).stdout.strip()


@pytest.fixture
def only_amd64(architecture):
    """Pretty way to skip ARM tests."""
    if architecture != "amd64":
        pytest.skip("Requires amd64 architecture")


@pytest.fixture
def only_arm64(architecture):
    """Pretty way to skip AMD tests."""
    if architecture != "arm64":
        pytest.skip("Requires arm64 architecture")


@pytest.fixture
def only_with_juju_secrets(juju_has_secrets):
    """Pretty way to skip Juju 3 tests."""
    if not juju_has_secrets:
        pytest.skip("Secrets test only applies on Juju 3.x")


@pytest.fixture
def only_without_juju_secrets(juju_has_secrets):
    """Pretty way to skip Juju 2-specific tests.

    Typically: to save CI time, when the same check were executed in a Juju 3-specific way already
    """
    if juju_has_secrets:
        pytest.skip("Skipping legacy secrets tests")
