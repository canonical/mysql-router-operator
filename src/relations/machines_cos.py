# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation to the cos charms."""

import logging
import typing

import charm_refresh
import common.container
import common.relations.cos
from charms.grafana_agent.v0.cos_agent import COSAgentProvider, charm_tracing_config

if typing.TYPE_CHECKING:
    import common.abstract_charm

logger = logging.getLogger(__name__)


class COSRelation(common.relations.cos.COSRelation):
    """Relation with the cos bundle."""

    _METRICS_RELATION_NAME = "cos-agent"

    def __init__(
        self,
        charm_: "common.abstract_charm.MySQLRouterCharm",
        container_: common.container.Container,
    ):
        self._interface = COSAgentProvider(
            charm_,
            metrics_endpoints=[
                {
                    "path": "/metrics",
                    "port": self._EXPORTER_PORT,
                }
            ],
            log_slots=[f"{charm_refresh.snap_name()}:logs"],
            tracing_protocols=[self._TRACING_PROTOCOL],
        )
        super().__init__(charm_=charm_, container_=container_)

        self._tracing_endpoint, _ = charm_tracing_config(self._interface, None)

    @property
    def tracing_endpoint(self) -> typing.Optional[str]:
        return self._tracing_endpoint
