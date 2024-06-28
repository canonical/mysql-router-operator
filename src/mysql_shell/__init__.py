# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Shell in Python execution mode

https://dev.mysql.com/doc/mysql-shell/8.0/en/
"""

import dataclasses
import json
import logging
import pathlib
import typing

import jinja2

import container
import server_exceptions
import utils

if typing.TYPE_CHECKING:
    import relations.database_requires

logger = logging.getLogger(__name__)


# TODO python3.10 min version: Add `(kw_only=True)`
@dataclasses.dataclass
class RouterUserInformation:
    """MySQL Router user information"""

    username: str
    router_id: str


class ShellDBError(Exception):
    """`mysqlsh.DBError` raised while executing MySQL Shell script

    MySQL Shell runs Python code in a separate process from the charm Python code.
    The `mysqlsh.DBError` was caught by the shell code, serialized to JSON, and de-serialized to
    this exception.
    """

    def __init__(self, *, message: str, code: int, traceback_message: str):
        super().__init__(message)
        self.code = code
        self.traceback_message = traceback_message


# TODO python3.10 min version: Add `(kw_only=True)`
@dataclasses.dataclass
class Shell:
    """MySQL Shell connected to MySQL cluster"""

    _container: container.Container
    _connection_info: "relations.database_requires.CompleteConnectionInformation"

    @property
    def username(self):
        return self._connection_info.username

    def _run_code(self, code: str) -> None:
        """Connect to MySQL cluster and run Python code."""
        template = _jinja_env.get_template("try_except_wrapper.py.jinja")
        error_file = self._container.path("/tmp/mysqlsh_error.json")

        def render(connection_info: "relations.database_requires.ConnectionInformation"):
            return template.render(
                username=connection_info.username,
                password=connection_info.password,
                host=connection_info.host,
                port=connection_info.port,
                code=code,
                error_filepath=error_file.relative_to_container,
            )

        # Redact password from log
        logged_script = render(self._connection_info.redacted)

        script = render(self._connection_info)
        temporary_script_file = self._container.path("/tmp/mysqlsh_script.py")
        error_file = self._container.path("/tmp/mysqlsh_error.json")
        temporary_script_file.write_text(script)
        try:
            self._container.run_mysql_shell(
                [
                    "--no-wizard",
                    "--python",
                    "--file",
                    str(temporary_script_file.relative_to_container),
                ]
            )
        except container.CalledProcessError as e:
            logger.exception(
                f"Failed to run MySQL Shell script:\n{logged_script}\n\nstderr:\n{e.stderr}\n"
            )
            raise
        finally:
            temporary_script_file.unlink()
        with error_file.open("r") as file:
            exception = json.load(file)
        error_file.unlink()
        try:
            if exception:
                raise ShellDBError(**exception)
        except ShellDBError as e:
            if e.code == 2003:
                logger.exception(server_exceptions.ConnectionError.MESSAGE)
                raise server_exceptions.ConnectionError
            else:
                logger.exception(
                    f"Failed to run MySQL Shell script:\n{logged_script}\n\nMySQL client error {e.code}\nMySQL Shell traceback:\n{e.traceback_message}\n"
                )
                raise

    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _run_sql(self, sql_statements: typing.List[str]) -> None:
        """Connect to MySQL cluster and execute SQL."""
        self._run_code(
            _jinja_env.get_template("run_sql.py.jinja").render(statements=sql_statements)
        )

    def _get_attributes(self, additional_attributes: dict = None) -> str:
        """Attributes for (MySQL) users created by this charm

        If the relation with the MySQL charm is broken, the MySQL charm will use this attribute
        to delete all users created by this charm.
        """
        attributes = {"created_by_user": self.username}
        if additional_attributes:
            attributes.update(additional_attributes)
        return json.dumps(attributes)

    def create_application_database_and_user(self, *, username: str, database: str) -> str:
        """Create database and user for related database_provides application."""
        attributes = self._get_attributes()
        logger.debug(f"Creating {database=} and {username=} with {attributes=}")
        password = utils.generate_password()
        self._run_sql(
            [
                f"CREATE DATABASE IF NOT EXISTS `{database}`",
                f"CREATE USER `{username}` IDENTIFIED BY '{password}' ATTRIBUTE '{attributes}'",
                f"GRANT ALL PRIVILEGES ON `{database}`.* TO `{username}`",
            ]
        )
        logger.debug(f"Created {database=} and {username=} with {attributes=}")
        return password

    def add_attributes_to_mysql_router_user(
        self, *, username: str, router_id: str, unit_name: str
    ) -> None:
        """Add attributes to user created during MySQL Router bootstrap."""
        attributes = self._get_attributes(
            {"router_id": router_id, "created_by_juju_unit": unit_name}
        )
        logger.debug(f"Adding {attributes=} to {username=}")
        self._run_sql([f"ALTER USER `{username}` ATTRIBUTE '{attributes}'"])
        logger.debug(f"Added {attributes=} to {username=}")

    def get_mysql_router_user_for_unit(
        self, unit_name: str
    ) -> typing.Optional[RouterUserInformation]:
        """Get MySQL Router user created by a previous instance of the unit.

        Get username & router ID attribute.

        Before container restart, the charm does not have an opportunity to delete the MySQL
        Router user or cluster metadata created during MySQL Router bootstrap. After container
        restart, the user and cluster metadata should be deleted before bootstrapping MySQL Router
        again.
        """
        logger.debug(f"Getting MySQL Router user for {unit_name=}")
        output_file = self._container.path("/tmp/mysqlsh_output.json")
        self._run_code(
            _jinja_env.get_template("get_mysql_router_user_for_unit.py.jinja").render(
                username=self.username,
                unit_name=unit_name,
                output_filepath=output_file.relative_to_container,
            )
        )
        with output_file.open("r") as file:
            rows = json.load(file)
        output_file.unlink()
        if not rows:
            logger.debug(f"No MySQL Router user found for {unit_name=}")
            return
        assert len(rows) == 1
        username, router_id = rows[0]
        user_info = RouterUserInformation(username=username, router_id=router_id)
        logger.debug(f"MySQL Router user found for {unit_name=}: {user_info}")
        return user_info

    def remove_router_from_cluster_metadata(self, router_id: str) -> None:
        """Remove MySQL Router from InnoDB Cluster metadata.

        On container restart, MySQL Router bootstrap will fail without `--force` if cluster
        metadata already exists for the router ID.
        """
        logger.debug(f"Removing {router_id=} from cluster metadata")
        self._run_code(
            _jinja_env.get_template("remove_router_from_cluster_metadata.py.jinja").render(
                router_id=router_id
            )
        )
        logger.debug(f"Removed {router_id=} from cluster metadata")

    def does_user_exists(self, username: str, host: str = "%") -> bool:
        """Check if user exists."""
        logger.debug(f"Checking if {username=} exists")
        output_file = self._container.path("/tmp/mysqlsh_output.json")
        self._run_code(
            _jinja_env.get_template("does_user_exist.py.jinja").render(
                username=username,
                host=host,
                output_filepath=output_file.relative_to_container,
            )
        )
        with output_file.open("r") as file:
            rows = json.load(file)
        output_file.unlink()
        if not rows:
            return False
        return True

    def delete_user(self, username: str, *, must_exist=True) -> None:
        """Delete user."""
        logger.debug(f"Deleting {username=} {must_exist=}")
        if must_exist:
            statement = f"DROP USER `{username}`"
        else:
            statement = f"DROP USER IF EXISTS `{username}`"
        self._run_sql([statement])
        logger.debug(f"Deleted {username=} {must_exist=}")

    def is_router_in_cluster_set(self, router_id: str) -> bool:
        """Check if MySQL Router is part of InnoDB ClusterSet."""
        logger.debug(f"Checking if {router_id=} in cluster set")
        output_file = self._container.path("/tmp/mysqlsh_output.json")
        self._run_code(
            _jinja_env.get_template("get_routers_in_cluster_set.py.jinja").render(
                output_filepath=output_file.relative_to_container
            )
        )
        with output_file.open("r") as file:
            output = json.load(file)
        output_file.unlink()
        cluster_set_router_ids = output["routers"].keys()
        logger.debug(f"{cluster_set_router_ids=}")
        logger.debug(f"Checked if {router_id in cluster_set_router_ids=}")
        return router_id in cluster_set_router_ids


_jinja_env = jinja2.Environment(
    autoescape=False,
    trim_blocks=True,
    loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent / "templates"),
    undefined=jinja2.StrictUndefined,
)
