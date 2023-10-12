# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Logrotate abstractions"""

import abc


class LogRotate(abc.ABC):
    """Abstraction for logrotate in MySQLRouter."""

    @abc.abstractmethod
    def setup_logrotate(self) -> None:
        """Set up logrotate."""

    @abc.abstractmethod
    def enable_logrotate(self) -> None:
        """Enable logrotate."""

    @abc.abstractmethod
    def disable_logrotate(self) -> None:
        """Disable logrotate."""
