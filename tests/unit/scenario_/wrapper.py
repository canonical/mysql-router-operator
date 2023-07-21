# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import dataclasses

import scenario


@dataclasses.dataclass
class Relation:
    """Wrapper for `scenario.Relation`

    Read-write dataclass (frozen=False)
    """

    endpoint: str
    local_app_data: dict[str, str] = dataclasses.field(default_factory=dict)
    local_unit_data: dict[str, str] = dataclasses.field(default_factory=dict)
    remote_app_name: str = "remote"
    remote_app_data: dict[str, str] = dataclasses.field(default_factory=dict)

    def freeze(self) -> scenario.Relation:
        """Convert to read-only `scenario.Relation` dataclass"""
        return scenario.Relation(**dataclasses.asdict(self))


@dataclasses.dataclass
class SubordinateRelation(Relation):
    """Wrapper for `scenario.SubordinateRelation`

    Read-write dataclass (frozen=False)
    """

    def freeze(self) -> scenario.SubordinateRelation:
        """Convert to read-only `scenario.SubordinateRelation` dataclass"""
        return scenario.SubordinateRelation(**dataclasses.asdict(self))
