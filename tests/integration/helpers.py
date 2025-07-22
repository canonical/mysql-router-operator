# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import itertools
import logging
import subprocess
import tempfile
from typing import Dict, List, Optional

import tenacity
from juju.unit import Unit
from pytest_operator.plugin import OpsTest

from .connector import MySQLConnector
from .juju_ import is_3_or_higher, run_action

logger = logging.getLogger(__name__)

CONTINUOUS_WRITES_DATABASE_NAME = "continuous_writes_database"
CONTINUOUS_WRITES_TABLE_NAME = "data"

MYSQL_DEFAULT_APP_NAME = "mysql"
MYSQL_ROUTER_DEFAULT_APP_NAME = "mysql-router"
APPLICATION_DEFAULT_APP_NAME = "mysql-test-app"


async def get_server_config_credentials(unit: Unit) -> Dict:
    """Helper to run an action to retrieve server config credentials from mysql unit.

    Must be run with a mysql unit.

    Args:
        unit: The juju unit on which to run the get-password action for server-config credentials

    Returns:
        A dictionary with the server config username and password
    """
    return await run_action(unit, "get-password", username="serverconfig")


async def get_inserted_data_by_application(unit: Unit) -> Optional[str]:
    """Helper to run an action to retrieve inserted data by the application.

    Args:
        unit: The juju unit on which to run the get-inserted-data action

    Returns:
        A string representing the inserted data
    """
    return (await run_action(unit, "get-inserted-data")).get("data")


async def execute_queries_against_unit(
    unit_address: str,
    username: str,
    password: str,
    queries: List[str],
    port: int = 3306,
    commit: bool = False,
) -> List:
    """Execute given MySQL queries on a unit.

    Args:
        unit_address: The public IP address of the unit to execute the queries on
        username: The MySQL username
        password: The MySQL password
        queries: A list of queries to execute
        port: The port to connect to in order to execute queries
        commit: A keyword arg indicating whether there are any writes queries

    Returns:
        A list of rows that were potentially queried
    """
    config = {
        "user": username,
        "password": password,
        "host": unit_address,
        "port": port,
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

    await ops_test.juju("ssh", unit_name, "sudo", "find", path, "-maxdepth", "1", "-delete")


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
        "ssh", unit.name, "sudo", "chown", "snap_daemon:snap_daemon", path
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
        directory: The directory from which to run ls -la

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
    await ops_test.juju(
        "ssh",
        unit_name,
        "sudo",
        "pkill",
        "-9",
        "-f",
        "logrotate -f /etc/logrotate.d/flush_mysqlrouter_logs",
    )

    # hold execution until process is stopped
    for attempt in tenacity.Retrying(
        reraise=True, stop=tenacity.stop_after_attempt(45), wait=tenacity.wait_fixed(2)
    ):
        with attempt:
            if await get_process_pid(ops_test, unit_name, "logrotate"):
                raise Exception("Failed to stop the flush_mysql_logs logrotate process")


async def get_tls_certificate_issuer(
    ops_test: OpsTest,
    unit_name: str,
    socket: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    connect_args = f"-unix {socket}" if socket else f"-connect {host}:{port}"
    get_tls_certificate_issuer_commands = [
        "ssh",
        unit_name,
        f"openssl s_client -showcerts -starttls mysql {connect_args} < /dev/null | openssl x509 -text | grep Issuer",
    ]
    return_code, issuer, _ = await ops_test.juju(*get_tls_certificate_issuer_commands)
    assert return_code == 0, f"failed to get TLS certificate issuer on {unit_name=}"
    return issuer


def get_application_name(ops_test: OpsTest, application_name_substring: str) -> str:
    """Returns the name of the application with the provided application name.

    This enables us to retrieve the name of the deployed application in an existing model.

    Note: if multiple applications with the application name exist,
    the first one found will be returned.
    """
    for application in ops_test.model.applications:
        if application_name_substring == application:
            return application

    return ""


@tenacity.retry(stop=tenacity.stop_after_attempt(30), wait=tenacity.wait_fixed(5), reraise=True)
async def get_primary_unit(
    ops_test: OpsTest,
    unit: Unit,
    app_name: str,
) -> Unit:
    """Helper to retrieve the primary unit.

    Args:
        ops_test: The ops test object passed into every test case
        unit: A unit on which to run dba.get_cluster().status() on
        app_name: The name of the test application
        cluster_name: The name of the test cluster

    Returns:
        A juju unit that is a MySQL primary
    """
    units = ops_test.model.applications[app_name].units
    results = await run_action(unit, "get-cluster-status")

    primary_unit = None
    for k, v in results["status"]["defaultreplicaset"]["topology"].items():
        if v["memberrole"] == "primary":
            unit_name = f"{app_name}/{k.split('-')[-1]}"
            primary_unit = [unit for unit in units if unit.name == unit_name][0]
            break

    if not primary_unit:
        raise ValueError("Unable to find primary unit")
    return primary_unit


async def get_primary_unit_wrapper(ops_test: OpsTest, app_name: str, unit_excluded=None) -> Unit:
    """Wrapper for getting primary.

    Args:
        ops_test: The ops test object passed into every test case
        app_name: The name of the application
        unit_excluded: excluded unit to run command on
    Returns:
        The primary Unit object
    """
    logger.info("Retrieving primary unit")
    units = ops_test.model.applications[app_name].units
    if unit_excluded:
        # if defined, exclude unit from available unit to run command on
        # useful when the workload is stopped on unit
        unit = ({unit for unit in units if unit.name != unit_excluded.name}).pop()
    else:
        unit = units[0]

    primary_unit = await get_primary_unit(ops_test, unit, app_name)

    return primary_unit


async def get_max_written_value_in_database(
    ops_test: OpsTest, unit: Unit, credentials: dict
) -> int:
    """Retrieve the max written value in the MySQL database.

    Args:
        ops_test: The ops test framework
        unit: The MySQL unit on which to execute queries on
        credentials: Database credentials to use
    """
    unit_address = await unit.get_public_address()

    select_max_written_value_sql = [
        f"SELECT MAX(number) FROM `{CONTINUOUS_WRITES_DATABASE_NAME}`.`{CONTINUOUS_WRITES_TABLE_NAME}`;"
    ]

    output = await execute_queries_against_unit(
        unit_address,
        credentials["username"],
        credentials["password"],
        select_max_written_value_sql,
    )

    return output[0]


async def ensure_all_units_continuous_writes_incrementing(
    ops_test: OpsTest, mysql_units: Optional[List[Unit]] = None
) -> None:
    """Ensure that continuous writes is incrementing on all units.

    Also, ensure that all continuous writes up to the max written value is available
    on all units (ensure that no committed data is lost).
    """
    logger.info("Ensure continuous writes are incrementing")

    mysql_application_name = get_application_name(ops_test, MYSQL_DEFAULT_APP_NAME)

    if not mysql_units:
        mysql_units = ops_test.model.applications[mysql_application_name].units

    primary = await get_primary_unit_wrapper(ops_test, mysql_application_name)

    server_config_credentials = await get_server_config_credentials(mysql_units[0])

    last_max_written_value = await get_max_written_value_in_database(
        ops_test, primary, server_config_credentials
    )

    select_all_continuous_writes_sql = [
        f"SELECT * FROM `{CONTINUOUS_WRITES_DATABASE_NAME}`.`{CONTINUOUS_WRITES_TABLE_NAME}`"
    ]

    async with ops_test.fast_forward():
        for unit in mysql_units:
            for attempt in tenacity.Retrying(
                reraise=True, stop=tenacity.stop_after_delay(5 * 60), wait=tenacity.wait_fixed(10)
            ):
                with attempt:
                    # ensure that all units are up to date (including the previous primary)
                    unit_address = await unit.get_public_address()

                    # ensure the max written value is incrementing (continuous writes is active)
                    max_written_value = await get_max_written_value_in_database(
                        ops_test, unit, server_config_credentials
                    )
                    assert max_written_value > last_max_written_value, (
                        "Continuous writes not incrementing"
                    )

                    # ensure that the unit contains all values up to the max written value
                    all_written_values = set(
                        await execute_queries_against_unit(
                            unit_address,
                            server_config_credentials["username"],
                            server_config_credentials["password"],
                            select_all_continuous_writes_sql,
                        )
                    )
                    numbers = set(range(1, max_written_value))
                    assert numbers <= all_written_values, (
                        f"Missing numbers in database for unit {unit.name}"
                    )

                    last_max_written_value = max_written_value


def get_juju_status(model_name: str) -> str:
    """Return the juju status output.

    Args:
        model_name: The model for which to retrieve juju status for
    """
    return subprocess.check_output(["juju", "status", "--model", model_name], encoding="utf-8")


async def get_data_integrator_credentials(
    ops_test: OpsTest, data_integrator_app_name: str, avoid_unit: Optional[str] = None
) -> Dict:
    """Helper to get the credentials from the deployed data integrator"""
    for unit in ops_test.model.applications[data_integrator_app_name].units:
        if unit.name != avoid_unit:
            data_integrator_unit = unit
            break

    assert data_integrator_unit, "No valid data integrator units found to query creds"

    logger.info(f"Running get-credentials on {data_integrator_unit.name}")

    action = await data_integrator_unit.run_action(action_name="get-credentials")
    result = await action.wait()
    if is_3_or_higher:
        assert result.results["return-code"] == 0
    else:
        assert result.results["Code"] == "0"
    assert result.results["ok"] == "True"
    return result.results["mysql"]


async def get_machine_address(ops_test: OpsTest, unit: Unit) -> str:
    """Get the unit's machine's address."""
    _, output, _ = await ops_test.juju("machines")

    for line in output.splitlines():
        if unit.machine.hostname in line:
            return line.split()[2]

    assert False, "Unable to find the unit's machine"
