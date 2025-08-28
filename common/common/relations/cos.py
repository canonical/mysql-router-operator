# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation to the cos charms."""

import abc
import dataclasses
import typing

import ops

from .. import container, utils
from . import secrets

if typing.TYPE_CHECKING:
    from .. import abstract_charm


@dataclasses.dataclass
class ExporterConfig:
    """Configuration for the MySQL Router exporter"""

    url: str
    username: str
    password: str
    listen_port: str


class COSRelation(abc.ABC):
    """Relation with the cos bundle."""

    _EXPORTER_PORT = "9152"
    HTTP_SERVER_PORT = "8443"
    _PEER_RELATION_NAME = "cos"

    MONITORING_USERNAME = "monitoring"
    _MONITORING_PASSWORD_KEY = "monitoring-password"

    _TRACING_PROTOCOL = "otlp_http"

    @property
    @abc.abstractmethod
    def _METRICS_RELATION_NAME(self) -> str:  # noqa: N802
        pass

    @abc.abstractmethod
    def __init__(self, charm_: "abstract_charm.MySQLRouterCharm", container_: container.Container):
        self._charm = charm_
        self._container = container_

        self._secrets = secrets.RelationSecrets(
            charm_,
            self._PEER_RELATION_NAME,
            unit_secret_fields=[self._MONITORING_PASSWORD_KEY],
        )

    @property
    def exporter_user_config(self) -> ExporterConfig:
        """Returns user config needed for the router exporter service."""
        return ExporterConfig(
            url=f"https://127.0.0.1:{self.HTTP_SERVER_PORT}",
            username=self.MONITORING_USERNAME,
            password=self.get_monitoring_password(),
            listen_port=self._EXPORTER_PORT,
        )

    @property
    def relation_exists(self) -> bool:
        """Whether relation with cos exists."""
        return len(self._charm.model.relations.get(self._METRICS_RELATION_NAME, [])) == 1

    @property
    @abc.abstractmethod
    def tracing_endpoint(self) -> typing.Optional[str]:
        """The tracing endpoint."""

    def get_monitoring_password(self) -> str:
        """Gets the monitoring password from unit peer data, or generate and cache it."""
        monitoring_password = self._secrets.get_value(
            secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY
        )
        if monitoring_password:
            return monitoring_password

        monitoring_password = utils.generate_password()
        self._secrets.set_value(
            secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY, monitoring_password
        )
        return monitoring_password

    def reset_monitoring_password(self) -> None:
        """Reset the monitoring password from unit peer data."""
        self._secrets.set_value(secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY, None)

    def is_relation_breaking(self, event) -> bool:
        """Whether relation will be broken after the current event is handled."""
        if not self.relation_exists:
            return False

        return (
            isinstance(event, ops.RelationBrokenEvent)
            and event.relation.id == self._charm.model.relations[self._METRICS_RELATION_NAME][0].id
        )
