import abc
import pathlib
import subprocess
import typing


class Path(pathlib.PurePosixPath, abc.ABC):
    @property
    @abc.abstractmethod
    def relative_to_container(self) -> pathlib.PurePosixPath:
        """Path from container root (instead of machine root)

        Only differs from `self` on machine charm
        """

    @abc.abstractmethod
    def read_text(self) -> str:
        """Open the file in text mode, read it, and close the file."""

    @abc.abstractmethod
    def write_text(self, data: str):
        """Open the file in text mode, write to it, and close the file."""

    @abc.abstractmethod
    def unlink(self):
        """Remove this file or link."""

    @abc.abstractmethod
    def mkdir(self):
        """Create a new directory at this path."""

    @abc.abstractmethod
    def rmtree(self):
        """Recursively delete the directory tree at this path."""


class CalledProcessError(subprocess.CalledProcessError):
    """Command returned non-zero exit code"""

    def __init__(self, *, returncode: int, cmd: list[str], output: str, stderr: str) -> None:
        super().__init__(returncode=returncode, cmd=cmd, output=output, stderr=stderr)


class Container(abc.ABC):
    @property
    def router_config_directory(self) -> Path:
        return self.path("/etc/mysqlrouter")

    @property
    def router_config_file(self) -> Path:
        return self.router_config_directory / "mysqlrouter.conf"

    @property
    def tls_config_file(self) -> Path:
        return self.router_config_directory / "tls.conf"

    def __init__(self, *, mysql_router_command: str, mysql_shell_command: str) -> None:
        self._mysql_router_command = mysql_router_command
        self._mysql_shell_command = mysql_shell_command

    @property
    @abc.abstractmethod
    def ready(self) -> bool:
        """Whether container is ready

        Only applies to Kubernetes charm
        """

    @property
    @abc.abstractmethod
    def mysql_router_service_enabled(self) -> bool:
        """MySQL Router service status"""

    @abc.abstractmethod
    def update_mysql_router_service(self, *, enabled: bool, tls: bool = None) -> None:
        """Update and restart MySQL Router service.

        Args:
            enabled: Whether MySQL Router service is enabled
            tls: Whether TLS is enabled. Required if enabled=True
        """
        if enabled:
            assert tls is not None, "`tls` argument required when enabled=True"

    @abc.abstractmethod
    def _run_command(self, command: list[str], *, timeout: typing.Optional[int]) -> str:
        """Run command in container.

        Raises:
            CalledProcessError: Command returns non-zero exit code
        """

    def run_mysql_router(self, args: list[str], *, timeout: int = None) -> str:
        """Run MySQL Router command.

        Raises:
            CalledProcessError: Command returns non-zero exit code
        """
        args.insert(0, self._mysql_router_command)
        return self._run_command(args, timeout=timeout)

    def run_mysql_shell(self, args: list[str], *, timeout: int = None) -> str:
        """Run MySQL Shell command.

        Raises:
            CalledProcessError: Command returns non-zero exit code
        """
        args.insert(0, self._mysql_shell_command)
        return self._run_command(args, timeout=timeout)

    @abc.abstractmethod
    def path(self, *args) -> Path:
        pass
