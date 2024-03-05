# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation to MySQL charm"""

import logging
import typing

import charms.data_platform_libs.v0.data_interfaces as data_interfaces
import ops

import relations.remote_databag as remote_databag
import status_exception

if typing.TYPE_CHECKING:
    import abstract_charm

logger = logging.getLogger(__name__)


class _MissingRelation(status_exception.StatusException):
    """Relation to MySQL charm does (or will) not exist for this unit

    If this unit is tearing down, the relation could still exist for other units.
    """

    def __init__(self, *, endpoint_name: str) -> None:
        super().__init__(ops.BlockedStatus(f"Missing relation: {endpoint_name}"))


class _RelationBreaking(_MissingRelation):
    """Relation to MySQL charm will be broken for this unit after the current event is handled

    Relation currently exists

    If this unit is tearing down, the relation could still exist for other units.
    """


class ConnectionInformation:
    """Information for connection to MySQL cluster"""

    host: str
    port: str
    username: str
    password: str


class RedactedConnectionInformation(ConnectionInformation):
    """Connection information with redacted password

    Used for logging
    """

    def __init__(self, *, host: str, port: str, username: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = "***"


class CompleteConnectionInformation(ConnectionInformation):
    """Information for connection to MySQL cluster

    User has permission to:
    - Create databases & users
    - Grant all privileges on a database to a user
    (Different from user that MySQL Router runs with after bootstrap.)
    """

    def __init__(self, *, interface: data_interfaces.DatabaseRequires, event) -> None:
        relations = interface.relations
        endpoint_name = interface.relation_name
        if not relations:
            raise _MissingRelation(endpoint_name=endpoint_name)
        assert len(relations) == 1
        relation = relations[0]
        if isinstance(event, ops.RelationBrokenEvent) and event.relation.id == relation.id:
            # Relation will be broken after the current event is handled
            raise _RelationBreaking(endpoint_name=endpoint_name)
        # MySQL charm databag
        databag = remote_databag.RemoteDatabag(interface=interface, relation=relation)
        endpoints = databag["endpoints"].split(",")
        assert len(endpoints) == 1
        endpoint = endpoints[0]
        self.host = endpoint.split(":")[0]
        self.port = endpoint.split(":")[1]
        self.username = databag["username"]
        self.password = databag["password"]

    @property
    def redacted(self):
        """Connection information with redacted password"""
        return RedactedConnectionInformation(
            host=self.host, port=self.port, username=self.username
        )


class RelationEndpoint:
    """Relation endpoint for MySQL charm"""

    _NAME = "backend-database"

    def __init__(self, charm_: "abstract_charm.MySQLRouterCharm") -> None:
        self._interface = data_interfaces.DatabaseRequires(
            charm_,
            relation_name=self._NAME,
            # Database name disregarded by MySQL charm if "mysqlrouter" extra user role requested
            database_name="mysql_innodb_cluster_metadata",
            extra_user_roles="mysqlrouter",
        )
        charm_.framework.observe(charm_.on[self._NAME].relation_created, charm_.reconcile)
        charm_.framework.observe(self._interface.on.database_created, charm_.reconcile)
        charm_.framework.observe(self._interface.on.endpoints_changed, charm_.reconcile)
        charm_.framework.observe(charm_.on[self._NAME].relation_broken, charm_.reconcile)

    def get_connection_info(self, *, event) -> typing.Optional[CompleteConnectionInformation]:
        """Information for connection to MySQL cluster"""
        try:
            return CompleteConnectionInformation(interface=self._interface, event=event)
        except (_MissingRelation, remote_databag.IncompleteDatabag):
            return

    def is_relation_breaking(self, event) -> bool:
        """Whether relation will be broken after the current event is handled"""
        try:
            CompleteConnectionInformation(interface=self._interface, event=event)
        except _RelationBreaking:
            return True
        except (_MissingRelation, remote_databag.IncompleteDatabag):
            pass
        return False

    def get_status(self, event) -> typing.Optional[ops.StatusBase]:
        """Report non-active status."""
        try:
            CompleteConnectionInformation(interface=self._interface, event=event)
        except (_MissingRelation, remote_databag.IncompleteDatabag) as exception:
            return exception.status
