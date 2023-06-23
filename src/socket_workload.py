# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQl Router workload with Unix sockets enabled"""

import configparser
import io
import logging
import pathlib

import workload

logger = logging.getLogger(__name__)

class SocketWorkload(workload.Workload):
    """MySQl Router workload with Unix sockets enabled"""


class AuthenticatedSocketWorkload(workload.AuthenticatedWorkload, SocketWorkload):
    """Workload with connection to MySQL cluster and with Unix sockets enabled"""

    def _get_bootstrap_command(self, password: str) -> list[str]:
        command = super()._get_bootstrap_command(password)
        command.extend(
            [
                "--conf-bind-address",
                "127.0.0.1",
                "--conf-use-sockets",
                # For unix sockets, authentication fails on first connection if this option is not
                # set. Workaround for https://bugs.mysql.com/bug.php?id=107291
                "--conf-set-option",
                "DEFAULT.server_ssl_mode=PREFERRED",
            ]
        )
        return command

    def _update_configured_socket_file_locations(self) -> None:
        """Update configured socket file locations from `/tmp` to `/run/mysqlrouter`.

        Called after MySQL Router bootstrap & before MySQL Router service is enabled

        Change configured location of socket files before socket files are created by MySQL Router
        service.

        Needed since `/tmp` inside a snap is not accessible to non-root users. The socket files
        must be accessible to applications related via database_provides endpoint.
        """
        logger.debug("Updating configured socket file locations")
        config = configparser.ConfigParser()
        config.read_string(self._container.router_config_file.read_text())
        for section_name, section in config.items():
            if not section_name.startswith("routing:"):
                continue
            section["socket"] = str(
                self._container.path("/run/mysqlrouter") / pathlib.PurePath(section["socket"]).name
            )
        with io.StringIO() as output:
            config.write(output)
            self._container.router_config_file.write_text(output.getvalue())
        logger.debug("Updated configured socket file locations")

    def _bootstrap_router(self, *, tls: bool) -> None:
        super()._bootstrap_router(tls=tls)
        self._update_configured_socket_file_locations()
