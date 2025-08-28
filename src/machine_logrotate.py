# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""logrotate cron configuration"""

import logging

import jinja2

import container
import logrotate

logger = logging.getLogger(__name__)

CHARMED_MYSQL_COMMON_DIRECTORY = "/var/snap/charmed-mysql/common"
SYSTEM_USER = "snap_daemon"
ROOT_USER = "root"


class LogRotate(logrotate.LogRotate):
    """logrotate cron configuration"""

    def __init__(self, *, container_: container.Container):
        super().__init__(container_=container_)
        self._logrotate_config = self._container.path("/etc/logrotate.d/flush_mysqlrouter_logs")
        self._cron_file = self._container.path("/etc/cron.d/flush_mysqlrouter_logs")

    def enable(self) -> None:
        logger.debug("Creating logrotate config file")

        template = jinja2.Template(self._container.path("templates/logrotate.j2").read_text())

        log_file_path = self._container.path("/var/log/mysqlrouter/mysqlrouter.log")
        rendered = template.render(
            log_file_path=str(log_file_path),
            system_user=SYSTEM_USER,
        )
        self._logrotate_config.write_text(rendered)

        logger.debug("Created logrotate config file")
        logger.debug("Adding cron job for logrotate")

        # cron needs the file to be owned by root
        self._cron_file.write_text(
            "* * * * * snap_daemon logrotate -f -s /tmp/logrotate.status /etc/logrotate.d/flush_mysqlrouter_logs\n\n",
            user=ROOT_USER,
            group=ROOT_USER,
        )

        logger.debug("Added cron job for logrotate")

    def disable(self) -> None:
        logger.debug("Removing cron job for log rotation of mysqlrouter")
        self._logrotate_config.unlink(missing_ok=True)
        self._cron_file.unlink(missing_ok=True)
        logger.debug("Removed cron job for log rotation of mysqlrouter")
