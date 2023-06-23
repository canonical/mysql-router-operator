# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Workload snap container & installer"""

import logging
import pathlib
import shutil
import subprocess
import typing

import charms.operator_libs_linux.v2.snap as snap_lib
import ops
import tenacity

import container

logger = logging.getLogger(__name__)

_SNAP_NAME = "charmed-mysql"


class Installer:
    """Workload snap installer"""

    _SNAP_REVISION = "61"

    @property
    def _snap(self) -> snap_lib.Snap:
        return snap_lib.SnapCache()[_SNAP_NAME]

    def install(self, *, unit: ops.Unit):
        """Install snap."""
        if self._snap.present:
            logger.error(f"{_SNAP_NAME} snap already installed on machine. Installation aborted")
            raise Exception(f"Multiple {_SNAP_NAME} snap installs not supported on one machine")
        logger.debug(f"Installing {_SNAP_NAME=}, {self._SNAP_REVISION=}")
        unit.status = ops.MaintenanceStatus("Installing snap")

        def _set_retry_status(_) -> None:
            message = "Snap install failed. Retrying..."
            unit.status = ops.MaintenanceStatus(message)
            logger.debug(message)

        try:
            for attempt in tenacity.Retrying(
                stop=tenacity.stop_after_delay(60 * 5),
                wait=tenacity.wait_exponential(multiplier=10),
                retry=tenacity.retry_if_exception_type(snap_lib.SnapError),
                after=_set_retry_status,
                reraise=True,
            ):
                with attempt:
                    self._snap.ensure(
                        state=snap_lib.SnapState.Present, revision=self._SNAP_REVISION
                    )
        except snap_lib.SnapError:
            raise
        logger.debug(f"Installed {_SNAP_NAME=}, {self._SNAP_REVISION=}")

    def uninstall(self):
        """Uninstall snap."""
        logger.debug(f"Uninstalling {_SNAP_NAME=}")
        self._snap.ensure(state=snap_lib.SnapState.Absent)
        logger.debug(f"Uninstalled {_SNAP_NAME=}")


class _Path(pathlib.PosixPath, container.Path):
    _UNIX_USERNAME = "snap_daemon"

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
            parent = None
        if parent:
            assert str(path).startswith("/")
            path = super().__new__(cls, parent, path.relative_to("/"), **kwargs)
        path._container_parent = parent
        return path

    def __rtruediv__(self, other):
        return type(self)(other, self)

    @property
    def relative_to_container(self) -> pathlib.PurePosixPath:
        if parent := self._container_parent:
            return pathlib.PurePosixPath("/", self.relative_to(parent))
        return self

    def read_text(self, encoding="utf-8", *args, **kwargs) -> str:
        return super().read_text(encoding, *args, **kwargs)

    def write_text(self, data: str, encoding="utf-8", *args, **kwargs):
        return_value = super().write_text(data, encoding, *args, **kwargs)
        shutil.chown(self, user=self._UNIX_USERNAME, group=self._UNIX_USERNAME)
        return return_value

    def mkdir(self, *args, **kwargs) -> None:
        super().mkdir(*args, **kwargs)
        shutil.chown(self, user=self._UNIX_USERNAME, group=self._UNIX_USERNAME)

    def rmtree(self):
        shutil.rmtree(self)


class Snap(container.Container):
    """Workload snap container"""

    _SERVICE_NAME = "mysqlrouter-service"

    def __init__(self) -> None:
        super().__init__(
            mysql_router_command=f"{_SNAP_NAME}.mysqlrouter",
            mysql_shell_command=f"{_SNAP_NAME}.mysqlsh",
        )

    @property
    def ready(self) -> bool:
        return True

    @property
    def _snap(self) -> snap_lib.Snap:
        return snap_lib.SnapCache()[_SNAP_NAME]

    @property
    def mysql_router_service_enabled(self) -> bool:
        return self._snap.services[self._SERVICE_NAME]["active"]

    def update_mysql_router_service(self, *, enabled: bool, tls: bool = None) -> None:
        super().update_mysql_router_service(enabled=enabled, tls=tls)
        if tls:
            raise NotImplementedError  # TODO VM TLS
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
