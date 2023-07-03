# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm lifecycle

https://juju.is/docs/sdk/a-charms-life
"""

import ops


class Unit(ops.Object):
    """Unit lifecycle"""

    _stored = ops.StoredState()

    def __init__(self, charm: ops.CharmBase):
        super().__init__(charm, str(type(self)))
        self._charm = charm
        for relation in self.model.relations:
            self.framework.observe(
                self._charm.on[relation].relation_departed, self._on_relation_departed
            )

    def _on_relation_departed(self, event: ops.RelationDepartedEvent) -> None:
        if event.departing_unit == self._charm.unit:
            self._stored.tearing_down = True

    @property
    def tearing_down(self) -> bool:
        """Whether unit is tearing down

        Teardown event sequence:
        *-relation-departed -> *-relation-broken
        stop
        remove

        Workaround for https://bugs.launchpad.net/juju/+bug/1979811
        """
        try:
            return self._stored.tearing_down
        except AttributeError:
            return False
