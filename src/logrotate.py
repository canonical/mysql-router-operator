# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Logrotate abstractions"""

import abc


class LogRotate(abc.ABC):
    """Abstraction for logrotate in MySQLRouter."""

    @abc.abstractmethod
    def set_up_and_enable(self) -> None:
        """Set up logrotate."""

    @abc.abstractmethod
    def disable(self) -> None:
        """Disable logrotate."""
