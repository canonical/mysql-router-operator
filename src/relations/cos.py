# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation to the cos charms."""

import logging
import typing
from dataclasses import dataclass

import ops
import requests
import tenacity
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
    _HTTP_SERVER_PORT = "8443"
    _NAME = "cos-agent"
    _PEER_RELATION_NAME = "cos"

    _MONITORING_USERNAME = "monitoring"
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
            url=f"https://127.0.0.1:{self._HTTP_SERVER_PORT}",
            username=self._MONITORING_USERNAME,
            password=self._get_monitoring_password(),
        )

    @property
    def relation_exists(self) -> bool:
        """Whether relation with cos exists."""
        return len(self._charm.model.relations.get(self._NAME, [])) == 1

    def _get_monitoring_password(self) -> str:
        """Gets the monitoring password from unit peer data, or generate and cache it."""
        monitoring_password = self._secrets.get_secret(
            relations.secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY
        )
        if monitoring_password:
            return monitoring_password

        monitoring_password = utils.generate_password()
        self._secrets.set_secret(
            relations.secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY, monitoring_password
        )
        return monitoring_password

    def _reset_monitoring_password(self) -> None:
        """Reset the monitoring password from unit peer data."""
        self._secrets.set_secret(relations.secrets.UNIT_SCOPE, self._MONITORING_PASSWORD_KEY, None)

    def is_relation_breaking(self, event) -> bool:
        """Whether relation will be broken after the current event is handled."""
        if not self.relation_exists:
            return False

        return (
            isinstance(event, ops.RelationBrokenEvent)
            and event.relation.id == self._charm.model.relations[self._NAME][0].id
        )

    def is_relation_cos_related(self, event) -> bool:
        """Whether relation is related to the metrics endpoint."""
        if not self.relation_exists:
            return False

        return (
            hasattr(event, "relation")
            and event.relation.id == self._charm.model.relations[self._NAME][0].id
        )

    def _wait_until_http_server_authenticates(self) -> None:
        """Wait until the router HTTP server authenticates with the monitoring credentials."""
        logger.debug("Waiting until router HTTP server authenticates")
        try:
            for attempt in tenacity.Retrying(
                reraise=True,
                stop=tenacity.stop_after_delay(30),
                wait=tenacity.wait_fixed(5),
            ):
                with attempt:
                    # do not verify tls certs as default certs do not have 127.0.0.1
                    # in its list of IP SANs
                    response = requests.get(
                        f"https://127.0.0.1:{self._HTTP_SERVER_PORT}/api/20190715/routes",
                        auth=(self._MONITORING_USERNAME, self._get_monitoring_password()),
                        verify=False,
                    )
                    assert response.status_code == 200
                    assert "bootstrap_rw" in response.text
        except AssertionError:
            logger.exception("Unable to authenticate router HTTP server")
            raise
        else:
            logger.debug("Successfully authenticated router HTTP server")

    def setup_monitoring_user(self) -> None:
        """Set up a router REST API use for mysqlrouter exporter."""
        logger.debug("Setting up router REST API user for mysqlrouter exporter")
        self._container.set_mysql_router_rest_api_password(
            user=self._MONITORING_USERNAME,
            password=self._get_monitoring_password(),
        )
        self._wait_until_http_server_authenticates()
        logger.debug("Set up router REST API user for mysqlrouter exporter")

    def cleanup_monitoring_user(self) -> None:
        """Clean up router REST API user for mysqlrouter exporter."""
        logger.debug("Cleaning router REST API user for mysqlrouter exporter")
        self._container.set_mysql_router_rest_api_password(
            user=self._MONITORING_USERNAME,
            password=None,
        )
        self._reset_monitoring_password()
        logger.debug("Cleaned router REST API user for mysqlrouter exporter")
