# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest

from . import architecture

amd64_only = pytest.mark.skipif(
    architecture.architecture != "amd64", reason="Requires amd64 architecture"
)
arm64_only = pytest.mark.skipif(
    architecture.architecture != "arm64", reason="Requires arm64 architecture"
)
