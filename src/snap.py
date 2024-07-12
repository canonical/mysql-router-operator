# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Workload snap container & installer"""

import enum
import logging
import pathlib
import platform
import shutil
import subprocess
import typing

import charms.operator_libs_linux.v2.snap as snap_lib
import ops
import tenacity

import container

if typing.TYPE_CHECKING:
    import relations.cos

logger = logging.getLogger(__name__)

_SNAP_NAME = "charmed-mysql"
REVISIONS: typing.Dict[str, str] = {
    # Keep in sync with `workload_version` file
    "x86_64": "109",
    "aarch64": "110",
}
revision = REVISIONS[platform.machine()]
_snap = snap_lib.SnapCache()[_SNAP_NAME]
_UNIX_USERNAME = "snap_daemon"


class _RefreshVerb(str, enum.Enum):
    INSTALL = "install"
    UPGRADE = "upgrade"


def _refresh(*, unit: ops.Unit, verb: _RefreshVerb) -> None:
    # TODO python3.10 min version: use `removesuffix` instead of `rstrip`
    logger.debug(f'{verb.capitalize().rstrip("e")}ing {_SNAP_NAME=}, {revision=}')
    unit.status = ops.MaintenanceStatus(f'{verb.capitalize().rstrip("e")}ing snap')

    def _set_retry_status(_) -> None:
        message = f"Snap {verb} failed. Retrying..."
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
            _snap.ensure(state=snap_lib.SnapState.Present, revision=revision)
    _snap.hold()
    logger.debug(f'{verb.capitalize().rstrip("e")}ed {_SNAP_NAME=}, {revision=}')


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
    _refresh(unit=unit, verb=_RefreshVerb.INSTALL)
    installed_by_unit.write_text(unique_unit_name)
    logger.debug(f"Wrote {unique_unit_name=} to {installed_by_unit.name=}")


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

    def open(self, mode="r", buffering=-1, encoding="utf-8", *args, **kwargs):
        return super().open(mode, buffering, encoding, *args, **kwargs)

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

    def __init__(self, *, unit_name: str) -> None:
        super().__init__(
            mysql_router_command=f"{_SNAP_NAME}.mysqlrouter",
            mysql_shell_command=f"{_SNAP_NAME}.mysqlsh",
            mysql_router_password_command=f"{_SNAP_NAME}.mysqlrouter-passwd",
            unit_name=unit_name,
        )

    @property
    def ready(self) -> bool:
        return True

    @property
    def mysql_router_service_enabled(self) -> bool:
        return _snap.services[self._SERVICE_NAME]["active"]

    @property
    def mysql_router_exporter_service_enabled(self) -> bool:
        return _snap.services[self._EXPORTER_SERVICE_NAME]["active"]

    def update_mysql_router_service(self, *, enabled: bool, tls: bool = None) -> None:
        super().update_mysql_router_service(enabled=enabled, tls=tls)

        if tls:
            _snap.set({"mysqlrouter.extra-options": f"--extra-config {self.tls_config_file}"})
        else:
            _snap.unset("mysqlrouter.extra-options")

        router_is_running = _snap.services[self._SERVICE_NAME]["active"]

        if enabled:
            if router_is_running:
                _snap.restart([self._SERVICE_NAME])
            else:
                _snap.start([self._SERVICE_NAME], enable=True)
        else:
            _snap.stop([self._SERVICE_NAME], disable=True)

    def update_mysql_router_exporter_service(
        self,
        *,
        enabled: bool,
        config: "relations.cos.ExporterConfig" = None,
        tls: bool = None,
        key_filename: str = None,
        certificate_filename: str = None,
        certificate_authority_filename: str = None,
    ) -> None:
        super().update_mysql_router_exporter_service(
            enabled=enabled,
            config=config,
            tls=tls,
            key_filename=key_filename,
            certificate_filename=certificate_filename,
            certificate_authority_filename=certificate_authority_filename,
        )

        if enabled:
            _snap.set(
                {
                    "mysqlrouter-exporter.listen-port": config.listen_port,
                    "mysqlrouter-exporter.user": config.username,
                    "mysqlrouter-exporter.password": config.password,
                    "mysqlrouter-exporter.url": config.url,
                    "mysqlrouter-exporter.service-name": self._unit_name.replace("/", "-"),
                }
            )
            if tls:
                _snap.set(
                    {
                        "mysqlrouter.tls-cacert-path": certificate_authority_filename,
                        "mysqlrouter.tls-cert-path": certificate_filename,
                        "mysqlrouter.tls-key-path": key_filename,
                    }
                )
            else:
                _snap.unset("mysqlrouter.tls-cacert-path")
                _snap.unset("mysqlrouter.tls-cert-path")
                _snap.unset("mysqlrouter.tls-key-path")
            _snap.start([self._EXPORTER_SERVICE_NAME], enable=True)
        else:
            _snap.stop([self._EXPORTER_SERVICE_NAME], disable=True)
            _snap.unset("mysqlrouter-exporter.listen-port")
            _snap.unset("mysqlrouter-exporter.user")
            _snap.unset("mysqlrouter-exporter.password")
            _snap.unset("mysqlrouter-exporter.url")
            _snap.unset("mysqlrouter-exporter.service-name")
            _snap.unset("mysqlrouter.tls-cacert-path")
            _snap.unset("mysqlrouter.tls-cert-path")
            _snap.unset("mysqlrouter.tls-key-path")

    def upgrade(self, unit: ops.Unit) -> None:
        """Upgrade snap."""
        _refresh(unit=unit, verb=_RefreshVerb.UPGRADE)

    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _run_command(
        self,
        command: typing.List[str],
        *,
        timeout: typing.Optional[int],
        input: str = None,
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
