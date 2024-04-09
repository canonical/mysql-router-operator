# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation to the cos charms."""

import logging
import typing
from dataclasses import dataclass

import ops
from charms.grafana_agent.v0.cos_agent import COSAgentProvider

import container
import relations.secrets
import utils
from snap import _SNAP_NAME

if typing.TYPE_CHECKING:
    import abstract_charm

logger = logging.getLogger(__name__)


@dataclass
class ExporterConfig:
    """Configuration for the MySQL Router exporter"""

    url: str
    username: str
    password: str


class COSRelation:
    """Relation with the cos bundle."""

    _EXPORTER_PORT = "49152"
    HTTP_SERVER_PORT = "8443"
    _NAME = "cos-agent"
    _PEER_RELATION_NAME = "cos"

    MONITORING_USERNAME = "monitoring"
    _MONITORING_PASSWORD_KEY = "monitoring-password"

    def __init__(self, charm_: "abstract_charm.MySQLRouterCharm", container_: container.Container):
        self._interface = COSAgentProvider(
            charm_,
            metrics_endpoints=[
                {
                    "path": "/metrics",
                    "port": self._EXPORTER_PORT,
                }
            ],
            log_slots=[f"{_SNAP_NAME}:logs"],
        )
        self._charm = charm_
        self._container = container_

        charm_.framework.observe(
            charm_.on[self._NAME].relation_created,
            charm_.reconcile,
        )
        charm_.framework.observe(
            charm_.on[self._NAME].relation_broken,
            charm_.reconcile,
        )

        self._secrets = relations.secrets.RelationSecrets(
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
        )

    @property
    def relation_exists(self) -> bool:
        """Whether relation with cos exists."""
        return len(self._charm.model.relations.get(self._NAME, [])) == 1

    def get_monitoring_password(self) -> str:
        """Gets the monitoring password from unit peer data, or generate and cache it."""
        monitoring_password = self._secrets.get_value(
            relations.secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY
        )
        if monitoring_password:
            return monitoring_password

        monitoring_password = utils.generate_password()
        self._secrets.set_value(
            relations.secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY, monitoring_password
        )
        return monitoring_password

    def _reset_monitoring_password(self) -> None:
        """Reset the monitoring password from unit peer data."""
        self._secrets.set_value(relations.secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY, None)

    def is_relation_breaking(self, event) -> bool:
        """Whether relation will be broken after the current event is handled."""
        if not self.relation_exists:
            return False

        return (
            isinstance(event, ops.RelationBrokenEvent)
            and event.relation.id == self._charm.model.relations[self._NAME][0].id
        )
