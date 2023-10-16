# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""logrotate cron configuration"""

import logging

import jinja2

import logrotate

logger = logging.getLogger(__name__)

CHARMED_MYSQL_COMMON_DIRECTORY = "/var/snap/charmed-mysql/common"
SYSTEM_USER = "snap_daemon"
ROOT_USER = "root"


class LogRotate(logrotate.LogRotate):
    """logrotate cron configuration"""

    CRON_FILE_PATH = "/etc/cron.d/flush_mysqlrouter_logs"

    def enable(self) -> None:
        logger.debug("Creating logrotate config file")

        template = jinja2.Template(self._container.path("templates/logrotate.j2").read_text())

        log_file_path = self._container.path("/var/log/mysqlrouter/mysqlrouter.log")
        rendered = template.render(
            log_file_path=str(log_file_path),
            system_user=SYSTEM_USER,
        )
        logrotate_config = self._container.path("/etc/logrotate.d/flush_mysqlrouter_logs")
        logrotate_config.write_text(rendered, user=ROOT_USER, group=ROOT_USER)

        logger.debug("Created logrotate config file")
        logger.debug("Adding cron job for logrotate")

        cron_file = self._container.path(self.CRON_FILE_PATH)
        cron_file.write_text(
            "* * * * * root logrotate -f /etc/logrotate.d/flush_mysqlrouter_logs\n\n",
            user=ROOT_USER,
            group=ROOT_USER,
        )

        logger.debug("Added cron job for logrotate")

    def disable(self) -> None:
        logger.debug("Removing cron job for log rotation of mysqlrouter")
        self._container.path(self.CRON_FILE_PATH).unlink()
        logger.debug("Removed cron job for log rotation of mysqlrouter")
