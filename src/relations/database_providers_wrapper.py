# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation(s) to one or more application charms

Wraps modern interface (database_provides.py) and DEPRECATED legacy interface
(deprecated_shared_db_database_provides.py)
"""

import typing

import ops

import mysql_shell
import relations.database_provides

# `as` used to fix type checking circular import
import relations.deprecated_shared_db_database_provides as deprecated_shared_db_database_provides

if typing.TYPE_CHECKING:
    import abstract_charm


class RelationEndpoint:
    """Relation endpoints for application charm(s)

    Wraps modern interface (database_provides.py) endpoint and DEPRECATED legacy interface
    (deprecated_shared_db_database_provides.py) endpoint
    """

    def __init__(
        self,
        charm_: "abstract_charm.MySQLRouterCharm",
        database_provides: relations.database_provides.RelationEndpoint,
    ) -> None:
        self._database_provides = database_provides
        self._deprecated_shared_db = deprecated_shared_db_database_provides.RelationEndpoint(
            charm_
        )

    def external_connectivity(self, event) -> bool:
        """Whether any of the relations are marked as external."""
        return self._database_provides.external_connectivity(event)

    def update_endpoints(
        self,
        *,
        router_read_write_endpoints: str,
        router_read_only_endpoints: str,
        exposed_read_write_endpoints: str,
        exposed_read_only_endpoints: str,
    ) -> None:
        """Update the endpoints in the provides relationship databags."""
        self._database_provides.update_endpoints(
            router_read_write_endpoints=router_read_write_endpoints,
            router_read_only_endpoints=router_read_only_endpoints,
            exposed_read_write_endpoints=exposed_read_write_endpoints,
            exposed_read_only_endpoints=exposed_read_only_endpoints,
        )

    def reconcile_users(
        self,
        *,
        event,
        router_read_write_endpoints: str,
        router_read_only_endpoints: str,
        exposed_read_write_endpoints: str,
        exposed_read_only_endpoints: str,
        shell: mysql_shell.Shell,
    ) -> None:
        """Create requested users and delete inactive users.

        When the relation to the MySQL charm is broken, the MySQL charm will delete all users
        created by this charm. Therefore, this charm does not need to delete users when that
        relation is broken.
        """
        self._database_provides.reconcile_users(
            event=event,
            router_read_write_endpoints=router_read_write_endpoints,
            router_read_only_endpoints=router_read_only_endpoints,
            exposed_read_write_endpoints=exposed_read_write_endpoints,
            exposed_read_only_endpoints=exposed_read_only_endpoints,
            shell=shell,
        )
        self._deprecated_shared_db.reconcile_users(event=event, shell=shell)

    def delete_all_databags(self) -> None:
        """Remove connection information from all databags.

        Called when relation with MySQL is breaking

        When the MySQL relation is re-established, it could be a different MySQL cluster—new users
        will need to be created.
        """
        self._database_provides.delete_all_databags()
        self._deprecated_shared_db.delete_all_databags()

    def get_status(self, event) -> typing.Optional[ops.StatusBase]:
        """Report non-active status."""
        database_provides_status = self._database_provides.get_status(event)
        deprecated_shared_db_status = self._deprecated_shared_db.get_status(event)
        if (
            isinstance(deprecated_shared_db_status, ops.ActiveStatus)
            and isinstance(database_provides_status, ops.BlockedStatus)
            and database_provides_status.message.startswith("Missing relation:")
        ):
            return deprecated_shared_db_status
        if database_provides_status:
            return database_provides_status
        return deprecated_shared_db_status
