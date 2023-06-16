import configparser
import io
import pathlib

import workload


class SocketWorkload(workload.Workload):
    pass


class AuthenticatedSocketWorkload(workload.AuthenticatedWorkload, SocketWorkload):
    @property
    def read_write_endpoint(self) -> str:
        return f'file://{self._container.path("/run/mysqlrouter/mysql.sock")}'

    @property
    def read_only_endpoint(self) -> str:
        return f'file://{self._container.path("/run/mysqlrouter/mysqlro.sock")}'

    def _get_bootstrap_command(self, password: str):
        command = super()._get_bootstrap_command(password)
        command.extend(
            [
                "--conf-use-sockets",
                # For unix sockets, authentication fails on first connection if this option is not
                # set. Workaround for https://bugs.mysql.com/bug.php?id=107291
                "--conf-set-option",
                "DEFAULT.server_ssl_mode=PREFERRED",
            ]
        )
        return command

    def _change_socket_file_locations(self) -> None:
        # TODO: rename
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

    def _bootstrap_router(self, *, tls: bool) -> None:
        super()._bootstrap_router(tls=tls)
        self._change_socket_file_locations()
