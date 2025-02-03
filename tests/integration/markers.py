# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest

from . import architecture, juju_

juju_secrets = pytest.mark.skipif(not juju_.is_3_or_higher, reason="Requires juju secrets")
amd64_only = pytest.mark.skipif(
    architecture.architecture != "amd64", reason="Requires amd64 architecture"
)
arm64_only = pytest.mark.skipif(
    architecture.architecture != "arm64", reason="Requires arm64 architecture"
)
