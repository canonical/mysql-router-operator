# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""hacluster relation hooks and helpers."""

import json
import logging
from hashlib import shake_128
from ipaddress import IPv4Address, ip_address
from typing import Optional

import ops

HACLUSTER_RELATION_NAME = "hacluster"
HA_PEER_RELATION_NAME = "ha"

logger = logging.getLogger(__name__)


class HACluster(ops.Object):
    """Defines hacluster functunality."""

    def __init__(self, charm: ops.CharmBase):
        super().__init__(charm, HACLUSTER_RELATION_NAME)

        self.charm = charm

        self.framework.observe(
            charm.on[HACLUSTER_RELATION_NAME].relation_changed, self._on_changed
        )
        self.framework.observe(charm.on.config_changed, self._on_changed)

    @property
    def relation(self) -> ops.Relation:
        """Returns the relations in this model, or None if hacluster is not initialised."""
        return self.charm.model.get_relation(HACLUSTER_RELATION_NAME)

    @property
    def app_peer_relation(self) -> ops.RelationDataContent:
        """The HA peer relation app databag."""
        return self.charm.model.get_relation(HA_PEER_RELATION_NAME).data[self.charm.app]

    def is_set_up(self) -> bool:
        return self.relation and self.charm.config.get("vip")

    def _is_clustered(self) -> bool:
        for key, value in self.relation.data.items():
            if isinstance(key, ops.Unit) and key != self.charm.unit:
                if value.get("clustered") in ("yes", "true"):
                    return True
                break
        return False

    def _on_changed(self, event: ops.RelationChangedEvent | ops.RelationBrokenEvent) -> None:
        self.set_vip(self.charm.config.get("vip"))

    def get_unit_juju_status(self) -> ops.StatusBase:
        """Returns the status of the hacluster if relation exists."""
        if self.relation and not self.charm.is_externally_accessible(event=None):
            return ops.BlockedStatus("ha integration used without data-integrator")

        vip = self.charm.config.get("vip")
        if self.relation and not vip:
            return ops.BlockedStatus("ha integration used without vip configuration")

        if vip and not self.charm.is_externally_accessible(event=None):
            return ops.BlockedStatus("vip configuration without data-integrator")

        if self.charm.is_workload_authenticated and self.charm.unit.is_leader() and vip:
            return ops.ActiveStatus(f"VIP: {vip}")

    def set_vip(self, vip: Optional[str]) -> None:
        """Adds the requested virtual IP to the integration."""
        if not self.relation:
            return

        if not self._is_clustered():
            logger.debug("early exit set_vip: ha relation not yet clustered")
            return

        if vip:
            # TODO Add nic support
            ipaddr = ip_address(vip)
            vip_key = f"res_{self.charm.app.name}_{shake_128(vip.encode()).hexdigest(7)}_vip"
            vip_params = " params"
            if isinstance(ipaddr, IPv4Address):
                vip_resources = "ocf:heartbeat:IPaddr2"
                vip_params += f' ip="{vip}"'
            else:
                vip_resources = "ocf:heartbeat:IPv6addr"
                vip_params += f' ipv6addr="{vip}"'

            # Monitor the VIP
            vip_params += ' meta migration-threshold="INFINITY" failure-timeout="5s"'
            vip_params += ' op monitor timeout="20s" interval="10s" depth="0"'
            json_resources = json.dumps({vip_key: vip_resources})
            json_resource_params = json.dumps({vip_key: vip_params})

        else:
            json_resources = "{}"
            json_resource_params = "{}"

        self.relation.data[self.charm.unit].update(
            {
                "json_resources": json_resources,
                "json_resource_params": json_resource_params,
            }
        )
        self.charm.reconcile()
