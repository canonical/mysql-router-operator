# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""logrotate

https://manpages.ubuntu.com/manpages/jammy/man8/logrotate.8.html
"""

import abc

import container


class LogRotate(abc.ABC):
    """logrotate"""

    def __init__(self, *, container_: container.Container):
        self._container = container_

    @abc.abstractmethod
    def enable(self) -> None:
        """Enable logrotate."""

    @abc.abstractmethod
    def disable(self) -> None:
        """Disable logrotate."""
