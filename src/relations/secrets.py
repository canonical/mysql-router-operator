# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Secrets for MySQLRouter"""

import logging
import typing

import charms.data_platform_libs.v0.data_interfaces as data_interfaces

if typing.TYPE_CHECKING:
    import abstract_charm

logger = logging.getLogger(__name__)

APP_SCOPE = "app"
UNIT_SCOPE = "unit"
Scopes = typing.Literal[APP_SCOPE, UNIT_SCOPE]


class RelationSecrets:
    """MySQLRouter secrets on a specific peer relation"""

    _SECRET_INTERNAL_LABEL = "internal-secret"
    _SECRET_DELETED_LABEL = "None"

    def __init__(
        self,
        charm: "abstract_charm.MySQLRouterCharm",
        relation_name: str,
        app_secret_fields: typing.List[str] = [],
        unit_secret_fields: typing.List[str] = [],
    ) -> None:
        self._charm = charm
        self._relation_name = relation_name

        self._peer_relation_app = data_interfaces.DataPeer(
            charm,
            relation_name=relation_name,
            additional_secret_fields=app_secret_fields,
            deleted_label=self._SECRET_DELETED_LABEL,
        )
        self._peer_relation_unit = data_interfaces.DataPeerUnit(
            charm,
            relation_name=relation_name,
            additional_secret_fields=unit_secret_fields,
            deleted_label=self._SECRET_DELETED_LABEL,
        )

    def _peer_relation_data(self, scope: Scopes) -> data_interfaces.DataPeer:
        """Returns the peer relation data per scope."""
        if scope == APP_SCOPE:
            return self._peer_relation_app
        elif scope == UNIT_SCOPE:
            return self._peer_relation_unit

    def get_value(self, scope: Scopes, key: str) -> typing.Optional[str]:
        """Get secret from the secret storage."""
        if scope not in typing.get_args(Scopes):
            raise ValueError("Unknown secret scope")

        peers = self._charm.model.get_relation(self._relation_name)
        return self._peer_relation_data(scope).fetch_my_relation_field(peers.id, key)

    def set_value(
        self, scope: Scopes, key: str, value: typing.Optional[str]
    ) -> typing.Optional[str]:
        """Set secret from the secret storage."""
        if scope not in typing.get_args(Scopes):
            raise ValueError("Unknown secret scope")

        if not value:
            return self._remove_value(scope, key)

        peers = self._charm.model.get_relation(self._relation_name)
        self._peer_relation_data(scope).update_relation_data(peers.id, {key: value})

    def _remove_value(self, scope: Scopes, key: str) -> None:
        """Removing a secret."""
        if scope not in typing.get_args(Scopes):
            raise ValueError("Unknown secret scope")

        peers = self._charm.model.get_relation(self._relation_name)
        self._peer_relation_data(scope).delete_relation_data(peers.id, [key])
