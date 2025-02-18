# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Architecture utilities module"""

import logging
import os
import pathlib
import platform

import yaml
from ops.charm import CharmBase
from ops.model import BlockedStatus

logger = logging.getLogger(__name__)


class WrongArchitectureWarningCharm(CharmBase):
    """A fake charm class that only signals a wrong architecture deploy."""

    def __init__(self, *args):
        super().__init__(*args)

        hw_arch = platform.machine()
        self.unit.status = BlockedStatus(
            f"Charm incompatible with {hw_arch} architecture. "
            f"If this app is being refreshed, rollback"
        )
        raise RuntimeError(
            f"Incompatible architecture: this charm revision does not support {hw_arch}. "
            f"If this app is being refreshed, rollback with instructions from Charmhub docs. "
            f"If this app is being deployed for the first time, remove it and deploy it again "
            f"using a compatible revision."
        )


def is_wrong_architecture() -> bool:
    """Checks if charm was deployed on wrong architecture."""
    charm_path = os.environ.get("CHARM_DIR", "")
    manifest_path = pathlib.Path(charm_path, "manifest.yaml")

    if not manifest_path.exists():
        logger.error("Cannot check architecture: manifest file not found in %s", manifest_path)
        return False

    manifest = yaml.safe_load(manifest_path.read_text())

    manifest_archs = []
    for base in manifest["bases"]:
        base_archs = base.get("architectures", [])
        manifest_archs.extend(base_archs)

    hardware_arch = platform.machine()
    if ("amd64" in manifest_archs and hardware_arch == "x86_64") or (
        "arm64" in manifest_archs and hardware_arch == "aarch64"
    ):
        logger.debug("Charm architecture matches")
        return False

    logger.error("Charm architecture does not match")
    return True
