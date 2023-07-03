# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm lifecycle

https://juju.is/docs/sdk/a-charms-life
"""
import logging

import ops

logger = logging.getLogger(__name__)


class Unit(ops.Object):
    """Unit lifecycle

    NOTE: Instantiate this object before registering event observers.
    (If this object is accessed by a *-relation-departed observer, this object's observer needs to
    run first.)
    """

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
    def _tearing_down(self) -> bool:
        """Whether unit is tearing down"""
        try:
            return self._stored.tearing_down
        except AttributeError:
            return False

    @property
    def authorized_leader(self) -> bool:
        """Whether unit is authorized to act as leader

        Returns `False` if unit is tearing down and will be replaced by another leader

        Teardown event sequence:
        *-relation-departed -> *-relation-broken
        stop
        remove

        Workaround for https://bugs.launchpad.net/juju/+bug/1979811
        (Unit receives *-relation-broken event when relation still exists [for other units])
        """
        if not self._charm.unit.is_leader():
            return False
        logger.debug(
            f"Leadership lifecycle status {self._charm.app.planned_units()=}, {self._tearing_down=}"
        )
        if self._charm.app.planned_units() == 0:
            # Workaround for subordinate charms
            # After `juju remove-relation` with principal charm, each subordinate unit will get a
            # *-relation-departed event where `event.departing_unit == self._charm.unit` is `True`.
            # This unit will not be replaced by another leader after it tears down, so it should
            # act as a leader (e.g. handle user cleanup on *-relation-broken) now.
            return True
        return not self._tearing_down
