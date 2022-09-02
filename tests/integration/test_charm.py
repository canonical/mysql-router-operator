#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.


import logging

from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


async def test_trivial(ops_test: OpsTest):
    assert True
