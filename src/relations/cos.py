# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation to the cos charms."""

import logging
import typing

import charms.data_platform_libs.v0.secrets as secrets
import ops
from charms.grafana_agent.v0.cos_agent import COSAgentProvider

import utils
from snap import _SNAP_NAME

if typing.TYPE_CHECKING:
    import abstract_charm

logger = logging.getLogger(__name__)

MONITORING_USERNAME = "monitoring"
MONITORING_PASSWORD_KEY = "monitoring-password"


class COSRelation:
    """Relation with the cos bundle."""

    _EXPORTER_PORT = "49152"
    _HTTP_SERVER_PORT = "8443"
    _NAME = "cos-agent"

    def __init__(self, charm_: "abstract_charm.MySQLRouterCharm"):
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
        self.charm_ = charm_

        charm_.framework.observe(
            charm_.on[self._NAME].relation_created,
            charm_.reconcile_database_relations,
        )
        charm_.framework.observe(
            charm_.on[self._NAME].relation_broken,
            charm_.reconcile_database_relations,
        )

    @property
    def exporter_user_info(self) -> dict:
        """Returns user info needed for the router exporter service."""
        return {
            "url": f"https://127.0.0.1:{self._HTTP_SERVER_PORT}",
            "username": MONITORING_USERNAME,
            "password": self._get_monitoring_password(),
        }

    @property
    def relation_exists(self) -> bool:
        """Whether relation with cos exists."""
        return len(self.charm_.model.relations.get(self._NAME, [])) == 1

    def _get_monitoring_password(self) -> str:
        """Gets the monitoring password from unit peer data, or generate and cache it."""
        monitoring_password = self.charm_.get_secret(secrets.UNIT_SCOPE, MONITORING_PASSWORD_KEY)
        if monitoring_password:
            return monitoring_password

        monitoring_password = utils.generate_password()
        self.charm_.set_secret(secrets.UNIT_SCOPE, MONITORING_PASSWORD_KEY, monitoring_password)
        return monitoring_password

    def is_relation_breaking(self, event) -> bool:
        """Whether relation will be broken after the current event is handled."""
        if not self.relation_exists:
            return False

        return (
            isinstance(event, ops.RelationBrokenEvent)
            and event.relation.id == self.charm_.model.relations[self._NAME][0].id
        )

    def setup_monitoring_user(self) -> None:
        """Set up a router REST API use for mysqlrouter exporter."""
        logger.debug("Setting up router REST API user for mysqlrouter exporter")
        password = self._get_monitoring_password()
        credentials_file = self.charm_._container.path("/etc/mysqlrouter/rest_api_credentials")

        self.charm_._container._run_command(
            [
                self.charm_._container.mysql_router_password_command,
                "set",
                str(credentials_file),
                "monitoring",
            ],
            input=password,
            timeout=30,
        )
        logger.debug("Set up router REST API user for mysqlrouter exporter")

    def cleanup_monitoring_user(self) -> None:
        """Clean up router REST API user for mysqlrouter exporter."""
        credentials_file = self.charm_._container.path("/etc/mysqlrouter/rest_api_credentials")
        if not credentials_file.exists():
            return

        logger.debug("Cleaning router REST API user for mysqlrouter exporter")
        self.charm_._container._run_command(
            [
                self.charm_._container.mysql_router_password_command,
                "delete",
                str(credentials_file),
                "monitoring",
            ],
            timeout=30,
        )
        logger.debug("Cleaned router REST API user for mysqlrouter exporter")
