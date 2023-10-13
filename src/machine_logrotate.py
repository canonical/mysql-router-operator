# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Logrotate implementation for machine charm"""

import logging

import jinja2

import logrotate
from snap import _Path

logger = logging.getLogger(__name__)

CHARMED_MYSQL_COMMON_DIRECTORY = "/var/snap/charmed-mysql/common"
SYSTEM_USER = "snap_daemon"
ROOT_USER = "root"


class LogRotate(logrotate.LogRotate):
    """Log rotation in machine charm."""

    def set_up_and_enable(self) -> None:
        logger.debug("Creating logrotate config file")

        template_file = _Path("templates/logrotate.j2")
        template = jinja2.Template(template_file.read_text())

        log_file_path = _Path("/var/log/mysqlrouter/mysqlrouter.log")
        rendered = template.render(
            log_file_path=str(log_file_path),
            system_user=SYSTEM_USER,
        )
        logrotate_config = _Path("/etc/logrotate.d/flush_mysqlrouter_logs")
        logrotate_config.write_text(rendered, user=ROOT_USER, group=ROOT_USER)

        logger.debug("Created logrotate config file")
        logger.debug("Adding cron job for log rotation of mysqlrouter")

        cron = "* * * * * root logrotate -f /etc/logrotate.d/flush_mysqlrouter_logs\n\n"
        cron_file = _Path("/etc/cron.d/flush_mysqlrouter_logs")
        cron_file.write_text(cron, user=ROOT_USER, group=ROOT_USER)

        logger.debug("Added cron job for log rotation of mysqlrouter")

    def disable(self) -> None:
        logger.debug("Removing cron job for log rotation of mysqlrouter")
        _Path("/etc/cron.d/flush_mysqlrouter_logs").rmtree()
        logger.debug("Removed cron job for log rotation of mysqlrouter")
