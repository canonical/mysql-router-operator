#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

# TODO: re-enable when bug resolved: https://bugs.launchpad.net/charm-keystone/+bug/1990243
# import asyncio
# import logging
#
# import pytest
# from pytest_operator.plugin import OpsTest
#
# from .helpers import execute_queries_on_unit, get_server_config_credentials
#
# logger = logging.getLogger(__name__)
#
# MYSQL_APP_NAME = "mysql"
# KEYSTONE_APP_NAME = "keystone"
# MYSQLROUTER_APP_NAME = "mysqlrouter"
# TIMEOUT = 15 * 60
#
#
# @pytest.mark.group(1)
# @pytest.mark.abort_on_fail
# async def test_shared_db(ops_test: OpsTest, mysql_router_charm_series: str):
#     """Test the shared-db legacy relation."""
#     charm = await ops_test.build_charm(".")
#
#     mysql_app = await ops_test.model.deploy(
#         "mysql",
#         channel="8.0/edge",
#         application_name=MYSQL_APP_NAME,
#         config={"profile": "testing"},
#         num_units=1,
#     )
#     keystone_app = await ops_test.model.deploy(
#         "keystone", application_name=KEYSTONE_APP_NAME, series="focal", num_units=2
#     )
#     # MySQLRouter is a subordinate charm, and thus needs to be deployed with no units
#     # Instead, they will be deployed with the keystone units when related with the keystone app
#     mysqlrouter_app = await ops_test.model.deploy(
#         charm,
#         application_name=MYSQLROUTER_APP_NAME,
#         num_units=None,
#         series=mysql_router_charm_series,
#     )
#
#     await ops_test.model.relate(
#         f"{KEYSTONE_APP_NAME}:shared-db", f"{MYSQLROUTER_APP_NAME}:shared-db"
#     )
#
#     async with ops_test.fast_forward():
#         await asyncio.gather(
#             ops_test.model.wait_for_idle(
#                 apps=[MYSQL_APP_NAME],
#                 status="active",
#                 raise_on_blocked=True,
#                 timeout=TIMEOUT,
#                 wait_for_exact_units=1,
#             ),
#             ops_test.model.wait_for_idle(
#                 apps=[KEYSTONE_APP_NAME],
#                 status="blocked",
#                 timeout=TIMEOUT,
#                 wait_for_exact_units=2,
#             ),
#             ops_test.model.wait_for_idle(
#                 apps=[MYSQLROUTER_APP_NAME],
#                 status="active",
#                 timeout=TIMEOUT,
#             ),
#         )
#
#     await ops_test.model.relate(
#         f"{MYSQLROUTER_APP_NAME}:backend-database", f"{MYSQL_APP_NAME}:database"
#     )
#
#     async with ops_test.fast_forward():
#         await asyncio.gather(
#             ops_test.model.block_until(lambda: mysql_app.status == "active", timeout=TIMEOUT),
#             ops_test.model.block_until(lambda: keystone_app.status == "active", timeout=TIMEOUT),
#             ops_test.model.block_until(
#                 lambda: mysqlrouter_app.status == "active", timeout=TIMEOUT
#             ),
#         )
#
#     # Test that the keystone migration ran
#     get_count_keystone_tables_sql = [
#         "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'keystone'",
#     ]
#
#     mysql_unit = ops_test.model.applications[MYSQL_APP_NAME].units[0]
#     mysql_unit_address = await mysql_unit.get_public_address()
#
#     server_config_credentials = await get_server_config_credentials(mysql_unit)
#
#     output = await execute_queries_on_unit(
#         mysql_unit_address,
#         server_config_credentials["username"],
#         server_config_credentials["password"],
#         get_count_keystone_tables_sql,
#     )
#     assert output[0] > 0
