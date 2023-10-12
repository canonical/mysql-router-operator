# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import itertools
import tempfile
from typing import Dict, List

from juju.unit import Unit
from pytest_operator.plugin import OpsTest
from tenacity import RetryError, Retrying, stop_after_attempt, wait_fixed

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


async def get_process_pid(ops_test: OpsTest, unit_name: str, process: str) -> int:
    """Return the pid of a process running in a given unit.

    Args:
        ops_test: The ops test object passed into every test case
        unit_name: The name of the unit
        process: The process name to search for
    Returns:
        A integer for the process id
    """
    try:
        _, raw_pid, _ = await ops_test.juju("ssh", unit_name, "pgrep", "-x", process)
        pid = int(raw_pid.strip())

        return pid
    except Exception:
        return None


async def delete_file_or_directory_in_unit(ops_test: OpsTest, unit_name: str, path: str) -> bool:
    """Delete a file in the provided unit.

    Args:
        ops_test: The ops test framework
        unit_name: The name unit on which to delete the file from
        path: The path of file or directory to delete

    Returns:
        boolean indicating success
    """
    if path.strip() in ["/", "."]:
        return

    try:
        return_code, _, _ = await ops_test.juju(
            "ssh", unit_name, "sudo", "find", path, "-maxdepth", "1", "-delete"
        )

        return return_code == 0
    except Exception:
        return False


async def write_content_to_file_in_unit(
    ops_test: OpsTest, unit: Unit, path: str, content: str
) -> None:
    """Write content to the file in the provided unit.

    Args:
        ops_test: The ops test framework
        unit: THe unit in which to write to file in
        path: The path at which to write the content to
        content: The content to write to the file.
    """
    with tempfile.NamedTemporaryFile(mode="w") as temp_file:
        temp_file.write(content)
        temp_file.flush()

        await unit.scp_to(temp_file.name, "/tmp/file")

    return_code, _, _ = await ops_test.juju("ssh", unit.name, "sudo", "mv", "/tmp/file", path)
    assert return_code == 0

    return_code, _, _ = await ops_test.juju(
        "ssh", unit.name, "sudo", "chown", "snap_daemon:root", path
    )
    assert return_code == 0


async def read_contents_from_file_in_unit(ops_test: OpsTest, unit: Unit, path: str) -> str:
    """Read contents from file in the provided unit.

    Args:
        ops_test: The ops test framework
        unit: The unit in which to read file from
        path: The path from which to read content from

    Returns:
        the contents of the file
    """
    return_code, _, _ = await ops_test.juju("ssh", unit.name, "sudo", "cp", path, "/tmp/file")
    assert return_code == 0

    return_code, _, _ = await ops_test.juju(
        "ssh", unit.name, "sudo", "chown", "ubuntu:ubuntu", "/tmp/file"
    )
    assert return_code == 0

    with tempfile.NamedTemporaryFile(mode="r+") as temp_file:
        await unit.scp_from("/tmp/file", temp_file.name)

        temp_file.seek(0)

        contents = ""
        for line in temp_file:
            contents += line
            contents += "\n"

    return_code, _, _ = await ops_test.juju("ssh", unit.name, "sudo", "rm", "/tmp/file")
    assert return_code == 0

    return contents


async def ls_la_in_unit(ops_test: OpsTest, unit_name: str, directory: str) -> list[str]:
    """Returns the output of ls -la in unit.

    Args:
        ops_test: The ops test framework
        unit_name: The name of unit in which to run ls -la
        path: The path from which to run ls -la

    Returns:
        a list of files returned by ls -la
    """
    return_code, output, _ = await ops_test.juju("ssh", unit_name, "sudo", "ls", "-la", directory)
    assert return_code == 0

    ls_output = output.split("\n")[1:]

    return [
        line.strip("\r")
        for line in ls_output
        if len(line.strip()) > 0 and line.split()[-1] not in [".", ".."]
    ]


async def stop_running_flush_mysqlrouter_cronjobs(ops_test: OpsTest, unit_name: str) -> None:
    """Stop running any logrotate jobs that may have been triggered by cron.

    Args:
        ops_test: The ops test object passed into every test case
        unit_name: The name of the unit to be tested
    """
    # send TERM signal to mysql daemon, which trigger shutdown process
    await ops_test.juju(
        "ssh",
        unit_name,
        "sudo",
        "pkill",
        "-15",
        "-f",
        "logrotate -f /etc/logrotate.d/flush_mysqlrouter_logs",
    )

    # hold execution until process is stopped
    try:
        for attempt in Retrying(stop=stop_after_attempt(45), wait=wait_fixed(2)):
            with attempt:
                if await get_process_pid(ops_test, unit_name, "logrotate"):
                    raise Exception
    except RetryError:
        raise Exception("Failed to stop the flush_mysql_logs logrotate process.")
