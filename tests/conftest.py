# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
from argparse import ArgumentError


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
        raise ArgumentError(
            None,
            "--mysql-router-charm-series and --mysql-router-charm-bases-index must be given together",
        )
    # Note: Update defaults whenever charmcraft.yaml is changed
    if config.option.mysql_router_charm_series is None:
        config.option.mysql_router_charm_series = "jammy"
    if config.option.mysql_router_charm_bases_index is None:
        config.option.mysql_router_charm_bases_index = 1
