# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQl Router workload with Unix sockets enabled"""

import configparser
import io
import logging
import pathlib
import typing

import common.workload

if typing.TYPE_CHECKING:
    import common.relations.database_requires

logger = logging.getLogger(__name__)


class RunningMachineWorkload(common.workload.RunningWorkload):
    """Workload with connection to MySQL cluster and with Unix sockets enabled"""

    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _get_bootstrap_command(
        self, *, event, connection_info: "common.relations.database_requires.ConnectionInformation"
    ) -> typing.List[str]:
        command = super()._get_bootstrap_command(event=event, connection_info=connection_info)
        if self._charm.is_externally_accessible(event=event):
            command.extend([
                "--conf-bind-address",
                "0.0.0.0",
            ])
        else:
            command.extend([
                "--conf-use-sockets",
                # For unix sockets, authentication fails on first connection if this option is not
                # set. Workaround for https://bugs.mysql.com/bug.php?id=107291
                "--conf-set-option",
                "DEFAULT.server_ssl_mode=PREFERRED",
                "--conf-skip-tcp",
            ])
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

    def _bootstrap_router(self, *, event, tls: bool) -> None:
        super()._bootstrap_router(event=event, tls=tls)
        if not self._charm.is_externally_accessible(event=event):
            self._update_configured_socket_file_locations()
