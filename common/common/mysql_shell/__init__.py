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

from .. import container, server_exceptions, utils

if typing.TYPE_CHECKING:
    from ..relations import database_requires

_ROLE_DML = "charmed_dml"
_ROLE_READ = "charmed_read"
_ROLE_MAX_LENGTH = 32

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
    _connection_info: "database_requires.CompleteConnectionInformation"

    @property
    def username(self):
        return self._connection_info.username

    def _run_code(self, code: str) -> None:
        """Connect to MySQL cluster and run Python code."""
        template = _jinja_env.get_template("try_except_wrapper.py.jinja")
        error_file = self._container.path("/tmp/mysqlsh_error.json")

        script = template.render(code=code, error_filepath=error_file.relative_to_container)

        temporary_script_file = self._container.path("/tmp/mysqlsh_script.py")
        temporary_script_file.write_text(script)

        try:
            # https://bugs.mysql.com/bug.php?id=117429 details on why --no-wizard is omitted
            self._container.run_mysql_shell(
                [
                    "--passwords-from-stdin",
                    "--uri",
                    f"{self._connection_info.username}@{self._connection_info.host}:{self._connection_info.port}",
                    "--python",
                    "--file",
                    str(temporary_script_file.relative_to_container),
                ],
                input=self._connection_info.password,
            )
        except container.CalledProcessError as e:
            logger.exception(
                f"Failed to run MySQL Shell script:\n{script}\n\nstderr:\n{e.stderr}\n"
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
                logger.exception(server_exceptions.ConnectionError_.MESSAGE)
                raise server_exceptions.ConnectionError_
            else:
                logger.exception(
                    f"Failed to run MySQL Shell script:\n{script}\n\nMySQL client error {e.code}\nMySQL Shell traceback:\n{e.traceback_message}\n"
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

    # TODO python3.10 min version: Use `set` instead of `typing.Set`
    def _get_mysql_databases(self) -> typing.Set[str]:
        """Returns a set with the MySQL databases."""
        logger.debug(f"Getting MySQL databases")
        output_file = self._container.path("/tmp/mysqlsh_output.json")
        self._run_code(
            _jinja_env.get_template("get_mysql_databases.py.jinja").render(
                output_filepath=output_file.relative_to_container,
            )
        )
        with output_file.open("r") as file:
            rows = json.load(file)
        output_file.unlink()
        logger.debug(f"MySQL databases found: {len(rows)}")
        return {row[0] for row in rows}

    # TODO python3.10 min version: Use `set` instead of `typing.Set`
    def _get_mysql_roles(self, name_pattern: str) -> typing.Set[str]:
        """Returns a set with the MySQL roles."""
        logger.debug(f"Getting MySQL roles with {name_pattern=}")
        output_file = self._container.path("/tmp/mysqlsh_output.json")
        self._run_code(
            _jinja_env.get_template("get_mysql_roles_with_pattern.py.jinja").render(
                name_pattern=name_pattern,
                output_filepath=output_file.relative_to_container,
            )
        )
        with output_file.open("r") as file:
            rows = json.load(file)
        output_file.unlink()
        logger.debug(f"MySQL roles found for {name_pattern=}: {len(rows)}")
        return {row[0] for row in rows}

    def _build_application_database_dba_role(self, database: str) -> str:
        """Builds the database-level DBA role, given length constraints."""
        role_prefix = "charmed_dba"
        role_suffix = "XX"

        role_name_available = _ROLE_MAX_LENGTH - len(role_prefix) - len(role_suffix) - 2
        role_name_description = database[:role_name_available]
        role_name_collisions = self._get_mysql_roles(f"{role_prefix}_{role_name_description}_%")

        return "_".join((
            role_prefix,
            role_name_description,
            str(len(role_name_collisions)).zfill(len(role_suffix)),
        ))

    def _create_application_database(self, *, database: str) -> None:
        """Create database for related database_provides application."""
        if database in self._get_mysql_databases():
            return

        role_name = self._build_application_database_dba_role(database)
        statements = [
            f"CREATE ROLE `{role_name}`",
            f"CREATE DATABASE `{database}`",
            f"GRANT SELECT, INSERT, DELETE, UPDATE, EXECUTE ON `{database}`.* TO {role_name}",
            f"GRANT ALTER, ALTER ROUTINE, CREATE, CREATE ROUTINE, CREATE VIEW, DROP, INDEX, LOCK TABLES, REFERENCES, TRIGGER ON `{database}`.* TO {role_name}",
        ]

        mysql_roles = self._get_mysql_roles("charmed_%")
        if _ROLE_READ in mysql_roles:
            statements.append(
                f"GRANT SELECT ON `{database}`.* TO {_ROLE_READ}",
            )
        if _ROLE_DML in mysql_roles:
            statements.append(
                f"GRANT SELECT, INSERT, DELETE, UPDATE ON `{database}`.* TO {_ROLE_DML}",
            )

        logger.debug(f"Creating {database=}")
        self._run_sql(statements)
        logger.debug(f"Created {database=}")

    def _create_application_user(self, *, database: str, username: str) -> str:
        """Create database user for related database_provides application."""
        attributes = self._get_attributes()
        password = utils.generate_password()
        logger.debug(f"Creating {username=} with {attributes=}")
        self._run_sql([
            f"CREATE USER `{username}` IDENTIFIED BY '{password}' ATTRIBUTE '{attributes}'",
            f"GRANT ALL PRIVILEGES ON `{database}`.* TO `{username}`",
        ])
        logger.debug(f"Created {username=} with {attributes=}")
        return password

    def create_application_database(self, *, database: str, username: str) -> str:
        """Create both the database and the relation user, returning its password."""
        self._create_application_database(database=database)
        return self._create_application_user(database=database, username=username)

    def add_attributes_to_mysql_router_user(
        self, *, username: str, router_id: str, unit_name: str
    ) -> None:
        """Add attributes to user created during MySQL Router bootstrap."""
        attributes = self._get_attributes({
            "router_id": router_id,
            "created_by_juju_unit": unit_name,
        })
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
