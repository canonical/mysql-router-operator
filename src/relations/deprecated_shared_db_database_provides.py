# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""DEPRECATED relation(s) to one or more application charms

Uses DEPRECATED "mysql-shared" relation interface
"""

import logging
import typing

import common.mysql_shell
import common.relations.remote_databag as remote_databag
import common.status_exception
import ops

if typing.TYPE_CHECKING:
    import common.abstract_charm


class LogPrefix(logging.LoggerAdapter):
    """Add prefix to all log messages"""

    def process(self, msg, kwargs):
        return f"[DEPRECATED shared-db] {msg}", kwargs


logger = LogPrefix(logging.getLogger(__name__), extra=None)


class _RemoteUnitDatabag(remote_databag.RemoteDatabag):
    """Relation databag for remote unit"""

    def __init__(self, relation: ops.Relation) -> None:
        self._app_name = relation.app.name
        self._endpoint_name = relation.name
        if not relation.units:
            raise remote_databag.IncompleteDatabag(
                app_name=self._app_name, endpoint_name=self._endpoint_name
            )
        # Subordinate charms can only access principal unit's databag
        assert len(relation.units) == 1
        # Principal unit
        remote_unit = relation.units.copy().pop()
        dict.__init__(self, relation.data[remote_unit])


class _RelationBreaking(Exception):
    """Relation will be broken for this unit after the current event is handled

    If this unit is tearing down, the relation could still exist for other units.
    """


class _Relation:
    """Relation to one application charm"""

    def __init__(
        self,
        *,
        relation: ops.Relation,
        peer_relation_app_databag: ops.RelationDataContent,
    ) -> None:
        self._id = relation.id
        self._peer_app_databag = peer_relation_app_databag
        self._peer_databag_username_key = f"deprecated_shared_db_relation_{self._id}.username"
        self.peer_databag_password_key = f"deprecated_shared_db_relation_{self._id}.password"

    def __eq__(self, other) -> bool:
        if not isinstance(other, _Relation):
            return False
        return self._id == other._id


class _UnitThatNeedsUser(_Relation):
    """Related application unit that has needs user password"""

    def __init__(
        self,
        *,
        relation: ops.Relation,
        peer_relation_app_databag: ops.RelationDataContent,
        unit: ops.Unit,
    ) -> None:
        super().__init__(relation=relation, peer_relation_app_databag=peer_relation_app_databag)
        self._local_unit_databag = relation.data[unit]
        self._remote_unit_databag = _RemoteUnitDatabag(relation)
        assert len(relation.units) == 1
        self._remote_unit_name = relation.units.copy().pop().name

    def set_databag(
        self,
        *,
        password: str,
    ) -> None:
        """Share connection information with application charm."""
        logger.debug(f"Setting unit databag {self._id=} {self._remote_unit_name=}")
        self._local_unit_databag["allowed_units"] = self._remote_unit_name
        self._local_unit_databag["db_host"] = "127.0.0.1"
        self._local_unit_databag["db_port"] = "3306"
        self._local_unit_databag["wait_timeout"] = "28800"
        self._local_unit_databag["password"] = password
        logger.debug(f"Set unit databag {self._id=} {self._remote_unit_name=}")

    def delete_databag(self) -> None:
        logger.debug(f"Deleting unit databag {self._id=} {self._remote_unit_name=}")
        for key in ("allowed_units", "db_host", "db_port", "wait_timeout", "password"):
            self._local_unit_databag.pop(key, None)
        logger.debug(f"Deleted unit databag {self._id=} {self._remote_unit_name=}")


class _RelationThatRequestedUser(_UnitThatNeedsUser):
    """Related application charm that has requested a database & user

    Only instantiated on leader unit
    """

    def __init__(
        self,
        *,
        relation: ops.Relation,
        peer_relation_app_databag: ops.RelationDataContent,
        unit: ops.Unit,
        event,
    ) -> None:
        if isinstance(event, ops.RelationBrokenEvent) and event.relation.id == relation.id:
            raise _RelationBreaking
        super().__init__(
            relation=relation, unit=unit, peer_relation_app_databag=peer_relation_app_databag
        )
        self._database: str = self._remote_unit_databag["database"]
        self._username: str = self._peer_app_databag.setdefault(
            self._peer_databag_username_key, self._remote_unit_databag["username"]
        )

    def create_database_and_user(
        self,
        *,
        shell: common.mysql_shell.Shell,
    ) -> None:
        """Create database & user and update databag."""
        # Delete user if exists
        # (If the user was previously created by this charm—but the hook failed—the user will
        # persist in MySQL but will not persist in the databag. Therefore, we lose the user's
        # password and need to re-create the user.)
        logger.debug("Deleting user if exists before creating user")
        shell.delete_user(self._username, must_exist=False)
        logger.debug("Deleted user if exists before creating user")

        password = shell.create_application_database(
            database=self._database,
            username=self._username,
        )
        self._peer_app_databag[self.peer_databag_password_key] = password
        self.set_databag(password=password)


class _UserNotShared(Exception):
    """Database & user has not been provided to related application charm"""


class _RelationWithSharedUser(_Relation):
    """Related application charm that has been provided with a database & user"""

    def __init__(
        self,
        *,
        relation: ops.Relation,
        peer_relation_app_databag: ops.RelationDataContent,
    ) -> None:
        super().__init__(relation=relation, peer_relation_app_databag=peer_relation_app_databag)
        for key in (self._peer_databag_username_key, self.peer_databag_password_key):
            if key not in self._peer_app_databag:
                raise _UserNotShared

    def delete_databag(self) -> None:
        """Remove connection information from databag."""
        logger.debug(f"Deleting databag {self._id=}")
        self._peer_app_databag.pop(self._peer_databag_username_key)
        self._peer_app_databag.pop(self.peer_databag_password_key)
        logger.debug(f"Deleted databag {self._id=}")

    def delete_user(self, *, shell: common.mysql_shell.Shell) -> None:
        """Delete user and update databag."""
        username = self._peer_app_databag[self._peer_databag_username_key]
        logger.debug(f"Deleting user {username=}")
        # Delete user if exists
        # (If the user was previously deleted by this charm—but the hook failed—the user will be
        # deleted in MySQL but will persist in the databag.)
        shell.delete_user(username, must_exist=False)
        logger.debug(f"Deleted user {username=}")
        self.delete_databag()


class RelationEndpoint(ops.Object):
    """DEPRECATED relation endpoint for application charm(s)"""

    _NAME = "shared-db"
    _CREDENTIALS_PEER_RELATION_ENDPOINT_NAME = "deprecated-shared-db-credentials"

    def __init__(self, charm_: "common.abstract_charm.MySQLRouterCharm") -> None:
        super().__init__(charm_, self._NAME)
        self._relations = charm_.model.relations[self._NAME]
        if self._relations:
            logger.warning(
                "'mysql-shared' relation interface is DEPRECATED and will be removed in a future release. Use 'mysql_client' interface instead."
            )
        self._charm = charm_
        self.framework.observe(
            self._charm.on[self._CREDENTIALS_PEER_RELATION_ENDPOINT_NAME].relation_changed,
            self._update_unit_databag,
        )

    @property
    def _peer_app_databag(self) -> ops.RelationDataContent:
        return self._charm.model.get_relation(self._CREDENTIALS_PEER_RELATION_ENDPOINT_NAME).data[
            self._charm.app
        ]

    def _update_unit_databag(self, _) -> None:
        """Synchronize shared-db unit databag with peer app databag.

        The legacy shared-db interface was created before Juju implemented app databags.

        When a user is created by the leader unit, instead of directly saving the credentials to
        the shared-db app databag, it is saved to the credentials peer relation app databag. Then,
        each unit needs to update its shared-db unit databag.

        Note: There is one peer relation but there can be multiple shared-db relations.
        """
        logger.debug("Synchronizing unit databags")
        requested_users = []
        for relation in self._relations:
            try:
                requested_users.append(
                    _UnitThatNeedsUser(
                        relation=relation,
                        unit=self._charm.unit,
                        peer_relation_app_databag=self._peer_app_databag,
                    )
                )
            except remote_databag.IncompleteDatabag:
                pass
        for relation in requested_users:
            if password := self._peer_app_databag.get(relation.peer_databag_password_key):
                relation.set_databag(password=password)
            else:
                relation.delete_databag()
        logger.debug("Synchronized unit databags")

    @property
    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _shared_users(self) -> typing.List[_RelationWithSharedUser]:
        shared_users = []
        for relation in self._relations:
            try:
                shared_users.append(
                    _RelationWithSharedUser(
                        relation=relation,
                        peer_relation_app_databag=self._peer_app_databag,
                    )
                )
            except _UserNotShared:
                pass
        return shared_users

    def reconcile_users(
        self,
        *,
        event,
        shell: common.mysql_shell.Shell,
    ) -> None:
        """Create requested users and delete inactive users.

        When the relation to the MySQL charm is broken, the MySQL charm will delete all users
        created by this charm. Therefore, this charm does not need to delete users when that
        relation is broken.
        """
        logger.debug(f"Reconciling users {event=}")
        requested_users = []
        for relation in self._relations:
            try:
                requested_users.append(
                    _RelationThatRequestedUser(
                        relation=relation,
                        unit=self._charm.unit,
                        peer_relation_app_databag=self._peer_app_databag,
                        event=event,
                    )
                )
            except (
                _RelationBreaking,
                remote_databag.IncompleteDatabag,
            ):
                pass
        logger.debug(f"State of reconcile users {requested_users=}, {self._shared_users=}")
        for relation in requested_users:
            if relation not in self._shared_users:
                relation.create_database_and_user(
                    shell=shell,
                )
        for relation in self._shared_users:
            if relation not in requested_users:
                relation.delete_user(shell=shell)
        logger.debug(f"Reconciled users {event=}")

    def delete_all_databags(self) -> None:
        """Remove connection information from all databags.

        Called when relation with MySQL is breaking

        When the MySQL relation is re-established, it could be a different MySQL cluster—new users
        will need to be created.
        """
        logger.debug("Deleting all application databags")
        for relation in self._shared_users:
            # MySQL charm will delete user; just delete databag
            relation.delete_databag()
        logger.debug("Deleted all application databags")

    def get_status(self, event) -> typing.Optional[ops.StatusBase]:
        """Report non-active status."""
        requested_users = []
        exception_reporting_priority = (remote_databag.IncompleteDatabag,)
        # TODO python3.10 min version: Use `list` instead of `typing.List`
        exceptions: typing.List[common.status_exception.StatusException] = []
        for relation in self._relations:
            try:
                requested_users.append(
                    _RelationThatRequestedUser(
                        relation=relation,
                        unit=self._charm.unit,
                        peer_relation_app_databag=self._peer_app_databag,
                        event=event,
                    )
                )
            except _RelationBreaking:
                pass
            except exception_reporting_priority as exception:
                exceptions.append(exception)
        for exception_type in exception_reporting_priority:
            for exception in exceptions:
                if isinstance(exception, exception_type):
                    return exception.status
        if requested_users:
            return ops.ActiveStatus("'mysql-shared' interface deprecated")
