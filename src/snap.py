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
_REVISION = "90"  # v8.0.35
_snap = snap_lib.SnapCache()[_SNAP_NAME]
_UNIX_USERNAME = "snap_daemon"
REST_API_CREDENTIALS_FILE = "/etc/mysqlrouter/rest_api_credentials"
REST_API_CONF = "/etc/mysqlrouter/router_rest_api.conf"


def install(*, unit: ops.Unit, model_uuid: str):
    """Install snap."""
    installed_by_unit = pathlib.Path(
        "/var/snap", _SNAP_NAME, "common", "installed_by_mysql_router_charm_unit"
    )
    unique_unit_name = f"{model_uuid}_{unit.name}"
    # This charm can override/use an existing snap installation only if the snap was previously
    # installed by this charm.
    # Otherwise, the snap could be in use by another charm (e.g. MySQL Server charm, a different
    # MySQL Router charm).
    if _snap.present and not (
        installed_by_unit.exists() and installed_by_unit.read_text() == unique_unit_name
    ):
        logger.debug(
            f"{installed_by_unit.exists() and installed_by_unit.read_text()=} {unique_unit_name=}"
        )
        logger.error(f"{_SNAP_NAME} snap already installed on machine. Installation aborted")
        raise Exception(f"Multiple {_SNAP_NAME} snap installs not supported on one machine")
    logger.debug(f"Installing {_SNAP_NAME=}, {_REVISION=}")
    unit.status = ops.MaintenanceStatus("Installing snap")

    def _set_retry_status(_) -> None:
        message = "Snap install failed. Retrying..."
        unit.status = ops.MaintenanceStatus(message)
        logger.debug(message)

    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_delay(60 * 5),
        wait=tenacity.wait_exponential(multiplier=10),
        retry=tenacity.retry_if_exception_type(snap_lib.SnapError),
        after=_set_retry_status,
        reraise=True,
    ):
        with attempt:
            _snap.ensure(state=snap_lib.SnapState.Present, revision=_REVISION)
    installed_by_unit.write_text(unique_unit_name)
    logger.debug(f"Wrote {unique_unit_name=} to {installed_by_unit.name=}")
    _snap.hold()
    logger.debug(f"Installed {_SNAP_NAME=}, {_REVISION=}")


def uninstall():
    """Uninstall snap."""
    logger.debug(f"Uninstalling {_SNAP_NAME=}")
    _snap.ensure(state=snap_lib.SnapState.Absent)
    logger.debug(f"Uninstalled {_SNAP_NAME=}")


class _Path(pathlib.PosixPath, container.Path):
    def __new__(cls, *args, **kwargs):
        path = super().__new__(cls, *args, **kwargs)
        if args and isinstance(args[0], cls) and (parent_ := args[0]._container_parent):
            path._container_parent = parent_
        else:
            if str(path).startswith("/etc/mysqlrouter") or str(path).startswith(
                "/var/lib/mysqlrouter"
            ):
                parent = f"/var/snap/{_SNAP_NAME}/current"
            elif str(path).startswith("/run/mysqlrouter") or str(path).startswith(
                "/var/log/mysqlrouter"
            ):
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

    def __truediv__(self, other):
        return type(self)(self, other)

    def __rtruediv__(self, other):
        return type(self)(other, self)

    @property
    def relative_to_container(self) -> pathlib.PurePosixPath:
        if parent := self._container_parent:
            return pathlib.PurePosixPath("/", self.relative_to(parent))
        return self

    def read_text(self, encoding="utf-8", *args, **kwargs) -> str:
        return super().read_text(encoding, *args, **kwargs)

    def write_text(
        self,
        data: str,
        encoding="utf-8",
        *args,
        user=_UNIX_USERNAME,
        group=_UNIX_USERNAME,
        **kwargs,
    ):
        return_value = super().write_text(data, encoding, *args, **kwargs)
        shutil.chown(self, user=user, group=group)
        return return_value

    def mkdir(self, *args, **kwargs) -> None:
        super().mkdir(*args, **kwargs)
        shutil.chown(self, user=_UNIX_USERNAME, group=_UNIX_USERNAME)

    def rmtree(self):
        shutil.rmtree(self)


class Snap(container.Container):
    """Workload snap container"""

    _SERVICE_NAME = "mysqlrouter-service"
    _EXPORTER_SERVICE_NAME = "mysqlrouter-exporter"

    def __init__(self) -> None:
        super().__init__(
            mysql_router_command=f"{_SNAP_NAME}.mysqlrouter",
            mysql_shell_command=f"{_SNAP_NAME}.mysqlsh",
        )

    @property
    def mysql_router_password_command(self) -> str:
        return f"{_SNAP_NAME}.mysqlrouter-passwd"

    @property
    def ready(self) -> bool:
        return True

    @property
    def mysql_router_service_enabled(self) -> bool:
        return _snap.services[self._SERVICE_NAME]["active"]

    @property
    def mysql_router_exporter_service_enabled(self) -> bool:
        return _snap.services[self._EXPORTER_SERVICE_NAME]["active"]

    def update_mysql_router_service(
        self, *, enabled: bool, tls: bool = None, exporter: bool = None
    ) -> None:
        super().update_mysql_router_service(enabled=enabled, tls=tls)
        if tls:
            raise NotImplementedError  # TODO VM TLS
        if exporter:
            _snap.set(
                {
                    "mysqlrouter.extra-options": f"--extra-config {self.path(REST_API_CONF)}",
                }
            )
        else:
            _snap.unset("mysqlrouter.extra-options")
        if enabled:
            _snap.start([self._SERVICE_NAME], enable=True)
        else:
            _snap.stop([self._SERVICE_NAME], disable=True)

    def update_mysql_router_exporter_service_enabled(
        self, *, enabled: bool, exporter_config: dict = {}
    ) -> bool:
        if enabled:
            _snap.set(
                {
                    "mysqlrouter-exporter.user": exporter_config["username"],
                    "mysqlrouter-exporter.password": exporter_config["password"],
                    "mysqlrouter-exporter.url": exporter_config["url"],
                }
            )
            _snap.start([self._EXPORTER_SERVICE_NAME], enable=True)
        else:
            _snap.unset("mysqlrouter-exporter.user")
            _snap.unset("mysqlrouter-exporter.password")
            _snap.unset("mysqlrouter-exporter.url")
            _snap.stop([self._EXPORTER_SERVICE_NAME], disable=True)

    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _run_command(
        self,
        command: typing.List[str],
        *,
        timeout: typing.Optional[int],
        input: typing.Optional[str] = None,
    ) -> str:
        try:
            output = subprocess.run(
                command,
                input=input,
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
