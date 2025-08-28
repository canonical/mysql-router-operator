# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""logrotate

https://manpages.ubuntu.com/manpages/jammy/man8/logrotate.8.html
"""

import abc
import logging
import pathlib

import jinja2

from . import container

logger = logging.getLogger(__name__)


class LogRotate(abc.ABC):
    """logrotate"""

    def __init__(self, *, container_: container.Container):
        self._container = container_

        self._logrotate_config = self._container.path("/etc/logrotate.d/flush_mysqlrouter_logs")

    @property
    @abc.abstractmethod
    def _SYSTEM_USER(self) -> str:  # noqa
        """The system user that mysqlrouter runs as."""

    def enable(self) -> None:
        """Enable logrotate."""
        logger.debug("Creating logrotate config file")

        template = jinja2.Template(
            (pathlib.Path(__file__).parent / "templates/logrotate.j2").read_text()
        )

        log_file_path = self._container.path("/var/log/mysqlrouter/mysqlrouter.log")
        rendered = template.render(
            log_file_path=str(log_file_path),
            system_user=self._SYSTEM_USER,
        )
        self._logrotate_config.write_text(rendered)

        logger.debug("Created logrotate config file")

    def disable(self) -> None:
        """Disable logrotate."""
        self._logrotate_config.unlink(missing_ok=True)
