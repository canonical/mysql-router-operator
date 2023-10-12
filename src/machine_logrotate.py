# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Logrotate implementation for machine charm"""

import logging
import pathlib

import jinja2

import logrotate

logger = logging.getLogger(__name__)

CHARMED_MYSQL_COMMON_DIRECTORY = "/var/snap/charmed-mysql/common"
SYSTEM_USER = "snap_daemon"


class MachineLogRotate(logrotate.LogRotate):
    """Log rotation in machine charm."""

    def setup_logrotate(self) -> None:
        """Set up the logrotate config."""
        logger.debug("Setting up logrotate config file")

        with open("templates/logrotate.j2", "r") as file:
            template = jinja2.Template(file.read())

        rendered = template.render(
            snap_common_directory=CHARMED_MYSQL_COMMON_DIRECTORY,
            system_user=SYSTEM_USER,
        )

        with open("/etc/logrotate.d/flush_mysqlrouter_logs", "w") as file:
            file.write(rendered)

        logger.debug("Created logrotate config file")

    def enable_logrotate(self) -> None:
        """Enable log rotation by creating a cron job."""
        logger.debug("Adding cron job for log rotation of mysqlrouter")

        cron = "* * * * * root logrotate -f /etc/logrotate.d/flush_mysqlrouter_logs\n"
        with open("/etc/cron.d/flush_mysqlrouter_logs", "w") as file:
            file.write(cron)

        logger.debug("Added cron job for log rotation of mysqlrouter")

    def disable_logrotate(self) -> None:
        """Disable log rotation by removing associated cron job."""
        logger.debug("Removing cron job for log rotation of mysqlrouter")
        pathlib.Path("/etc/cron.d/flush_mysqlrouter_logs").unlink(missing_ok=True)
        logger.debug("Removed cron job for log rotation of mysqlrouter")
