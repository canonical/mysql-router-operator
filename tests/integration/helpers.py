# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import itertools
from typing import Dict, List

from juju.unit import Unit

from .connector import MySQLConnector


async def get_server_config_credentials(unit: Unit) -> Dict:
    """Helper to run an action to retrieve server config credentials from mysql unit.

    Must be run with a mysql unit.

    Args:
        unit: The juju unit on which to run the get-password action for server-config credentials

    Returns:
        A dictionary with the server config username and password
    """
    action = await unit.run_action(action_name="get-password", username="serverconfig")
    result = await action.wait()

    return result.results


async def get_inserted_data_by_application(unit: Unit) -> str:
    """Helper to run an action to retrieve inserted data by the application.

    Args:
        unit: The juju unit on which to run the get-inserted-data action

    Returns:
        A string representing the inserted data
    """
    action = await unit.run_action("get-inserted-data")
    result = await action.wait()

    return result.results.get("data")


async def execute_queries_on_unit(
    unit_address: str,
    username: str,
    password: str,
    queries: List[str],
    commit: bool = False,
) -> List:
    """Execute given MySQL queries on a unit.

    Args:
        unit_address: The public IP address of the unit to execute the queries on
        username: The MySQL username
        password: The MySQL password
        queries: A list of queries to execute
        commit: A keyword arg indicating whether there are any writes queries

    Returns:
        A list of rows that were potentially queried
    """
    config = {
        "user": username,
        "password": password,
        "host": unit_address,
        "raise_on_warnings": False,
    }

    with MySQLConnector(config, commit) as cursor:
        for query in queries:
            cursor.execute(query)
        output = list(itertools.chain(*cursor.fetchall()))

    return output
