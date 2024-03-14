# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation to the cos charms."""

import logging
import typing
from dataclasses import dataclass

import ops
from charms.grafana_agent.v0.cos_agent import COSAgentProvider
from relations.secrets import UNIT_SCOPE

import constants
import container
import utils
from snap import _SNAP_NAME

if typing.TYPE_CHECKING:
    import abstract_charm

logger = logging.getLogger(__name__)

MONITORING_USERNAME = "monitoring"


@dataclass
class ExporterConfig:
    """Configuration for the MySQL Router exporter"""

    url: str
    username: str
    password: str


class COSRelation:
    """Relation with the cos bundle."""

    _EXPORTER_PORT = "49152"
    _HTTP_SERVER_PORT = "8443"
    _NAME = "cos-agent"

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
        self.charm = charm_
        self._container = container_

        charm_.framework.observe(
            charm_.on[self._NAME].relation_created,
            charm_.reconcile,
        )
        charm_.framework.observe(
            charm_.on[self._NAME].relation_broken,
            charm_.reconcile,
        )

    @property
    def exporter_user_info(self) -> dict:
        """Returns user info needed for the router exporter service."""
        return ExporterConfig(
            url=f"https://127.0.0.1:{self._HTTP_SERVER_PORT}",
            username=MONITORING_USERNAME,
            password=self._get_monitoring_password(),
        )

    @property
    def relation_exists(self) -> bool:
        """Whether relation with cos exists."""
        return len(self.charm.model.relations.get(self._NAME, [])) == 1

    def _get_monitoring_password(self) -> str:
        """Gets the monitoring password from unit peer data, or generate and cache it."""
        monitoring_password = self.charm.cos_secrets.get_secret(
            UNIT_SCOPE, constants.MONITORING_PASSWORD_KEY
        )
        if monitoring_password:
            return monitoring_password

        monitoring_password = utils.generate_password()
        self.charm.cos_secrets.set_secret(
            UNIT_SCOPE, constants.MONITORING_PASSWORD_KEY, monitoring_password
        )
        return monitoring_password

    def _reset_monitoring_password(self) -> None:
        """Reset the monitoring password from unit peer data."""
        self.charm.cos_secrets.set_secret(UNIT_SCOPE, constants.MONITORING_PASSWORD_KEY, None)

    def is_relation_breaking(self, event) -> bool:
        """Whether relation will be broken after the current event is handled."""
        if not self.relation_exists:
            return False

        return (
            isinstance(event, ops.RelationBrokenEvent)
            and event.relation.id == self.charm.model.relations[self._NAME][0].id
        )

    def setup_monitoring_user(self) -> None:
        """Set up a router REST API use for mysqlrouter exporter."""
        logger.debug("Setting up router REST API user for mysqlrouter exporter")
        self._container.set_mysql_router_rest_api_password(
            user=MONITORING_USERNAME,
            password=self._get_monitoring_password(),
        )
        logger.debug("Set up router REST API user for mysqlrouter exporter")

    def cleanup_monitoring_user(self) -> None:
        """Clean up router REST API user for mysqlrouter exporter."""
        logger.debug("Cleaning router REST API user for mysqlrouter exporter")
        self._container.set_mysql_router_rest_api_password(
            user=MONITORING_USERNAME,
            password=None,
        )
        self._reset_monitoring_password()
        logger.debug("Cleaned router REST API user for mysqlrouter exporter")
