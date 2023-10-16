# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Logrotate abstractions"""

import abc

import container


class LogRotate(abc.ABC):
    """Abstraction for logrotate in MySQLRouter."""

    def __init__(self, container_: container.Container):
        self._container = container_

    @abc.abstractmethod
    def set_up_and_enable(self) -> None:
        """Set up logrotate."""

    @abc.abstractmethod
    def disable(self) -> None:
        """Disable logrotate."""
