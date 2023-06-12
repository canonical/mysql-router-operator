import pathlib
import shutil
import subprocess
import typing

import charms.operator_libs_linux.v2.snap as snap_lib

import container

_UNIX_USERNAME = None  # TODO
_SNAP_NAME = "charmed-mysql"


class _SnapPath(pathlib.PosixPath):
    def __new__(cls, *args, **kwargs):
        path = super().__new__(cls, *args, **kwargs)
        if str(path).startswith("/etc/mysqlrouter") or str(path).startswith(
            "/var/lib/mysqlrouter"
        ):
            parent = f"/var/snap/{_SNAP_NAME}/current"
        elif str(path).startswith("/run"):
            parent = f"/var/snap/{_SNAP_NAME}/common"
        elif str(path).startswith("/tmp"):
            parent = f"/tmp/snap-private-tmp/snap.{_SNAP_NAME}"
        else:
            return path
        assert str(path).startswith("/")
        return super().__new__(cls, parent, path.relative_to("/"), **kwargs)

    def __rtruediv__(self, other):
        return type(self)(other, self)


class _Path(_SnapPath, container.Path):
    _UNIX_USERNAME = _UNIX_USERNAME

    def read_text(self, encoding="utf-8", *args) -> str:
        return super().read_text(encoding, *args)

    def write_text(self, data: str, encoding="utf-8", *args):
        return super().write_text(data, encoding, *args)

    # TODO: override unlink with not exists no fail?

    def rmtree(self):
        shutil.rmtree(self)


class Snap(container.Container):
    UNIX_USERNAME = _UNIX_USERNAME
    _SNAP_REVISION = "51"
    _SERVICE_NAME = "mysqlrouter-service"

    def __init__(self) -> None:
        super().__init__(
            mysql_router_command=f"{_SNAP_NAME}.mysqlrouter",
            mysql_shell_command=f"{_SNAP_NAME}.mysqlsh",
        )

    def ready(self) -> bool:
        return True

    @property
    def _snap(self) -> snap_lib.Snap:
        return snap_lib.SnapCache()[_SNAP_NAME]

    @property
    def mysql_router_service_enabled(self) -> bool:
        return self._snap.services[self._SERVICE_NAME]["active"]

    def update_mysql_router_service(self, *, enabled: bool, tls: bool = None) -> None:
        # TODO: uncomment when TLS is implemented
        # super().update_mysql_router_service(enabled=enabled, tls=tls)
        if tls is not None:
            raise NotImplementedError
        if enabled:
            self._snap.start([self._SERVICE_NAME], enable=True)
        else:
            self._snap.stop([self._SERVICE_NAME], disable=True)

    def _run_command(self, command: list[str], *, timeout: typing.Optional[int]) -> str:
        try:
            output = subprocess.run(
                command,
                capture_output=True,
                timeout=timeout,
                check=True,
                encoding="utf-8",
            ).stdout
        except subprocess.CalledProcessError as e:
            raise container.CalledProcessError(
                returncode=e.returncode, cmd=e.cmd, output=e.output, stderr=e.stderr
            )
        return output

    def path(self, *args, **kwargs) -> _Path:
        return _Path(*args, **kwargs)
