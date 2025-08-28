# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Workload snap container & installer"""

import logging
import pathlib
import shutil
import subprocess
import typing

import charm_refresh
import charms.operator_libs_linux.v2.snap as snap_lib
import common.container
import ops
import tenacity

if typing.TYPE_CHECKING:
    import common.relations.cos

logger = logging.getLogger(__name__)

_UNIX_USERNAME = "snap_daemon"


def _unique_unit_name(*, unit: ops.Unit, model_uuid: str):
    return f"{model_uuid}_{unit.name}"


def _raise_if_snap_installed_not_by_this_charm(*, unit: ops.Unit, model_uuid: str):
    """Raise exception if snap was not installed by this charm

    Assumes snap is installed
    """
    snap_name = charm_refresh.snap_name()
    installed_by_unit = pathlib.Path(
        "/var/snap", snap_name, "common", "installed_by_mysql_router_charm_unit"
    )

    if not (
        installed_by_unit.exists()
        and installed_by_unit.read_text() == _unique_unit_name(unit=unit, model_uuid=model_uuid)
    ):
        # The snap could be in use by another charm (e.g. MySQL Server charm, a different MySQL
        # Router charm).
        logger.debug(
            f"{installed_by_unit.exists() and installed_by_unit.read_text()=} "
            f"{_unique_unit_name(unit=unit, model_uuid=model_uuid)=}"
        )
        logger.error(f"{snap_name} snap already installed on machine. Installation aborted")
        raise Exception(f"Multiple {snap_name} snap installs not supported on one machine")


def uninstall():
    """Uninstall snap if installed"""
    snap_name = charm_refresh.snap_name()
    snap = snap_lib.SnapCache()[snap_name]

    logger.debug(f"Ensuring {snap_name=} is uninstalled")
    snap.ensure(state=snap_lib.SnapState.Absent)
    logger.debug(f"Ensured {snap_name=} is uninstalled")


class _Path(pathlib.PosixPath, common.container.Path):
    def __new__(cls, *args, **kwargs):
        path = super().__new__(cls, *args, **kwargs)
        snap_name = charm_refresh.snap_name()

        if args and isinstance(args[0], cls) and (parent_ := args[0]._container_parent):
            path._container_parent = parent_
        else:
            if str(path).startswith("/etc/mysqlrouter") or str(path).startswith(
                "/var/lib/mysqlrouter"
            ):
                parent = f"/var/snap/{snap_name}/current"
            elif str(path).startswith("/run/mysqlrouter") or str(path).startswith(
                "/var/log/mysqlrouter"
            ):
                parent = f"/var/snap/{snap_name}/common"
            elif str(path).startswith("/tmp"):
                parent = f"/tmp/snap-private-tmp/snap.{snap_name}"
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


class Snap(common.container.Container):
    """Workload snap container"""

    _SERVICE_NAME = "mysqlrouter-service"
    _EXPORTER_SERVICE_NAME = "mysqlrouter-exporter"

    def __init__(self, *, unit_name: str) -> None:
        self._snap_name = charm_refresh.snap_name()
        self._installed_by_unit = pathlib.Path(
            "/var/snap", self._snap_name, "common", "installed_by_mysql_router_charm_unit"
        )

        super().__init__(
            mysql_router_command=f"{self._snap_name}.mysqlrouter",
            mysql_shell_command=f"{self._snap_name}.mysqlsh",
            mysql_router_password_command=f"{self._snap_name}.mysqlrouter-passwd",
            unit_name=unit_name,
        )

    @property
    def _snap(self):
        return snap_lib.SnapCache()[self._snap_name]

    @property
    def ready(self) -> bool:
        return True

    @property
    def mysql_router_service_enabled(self) -> bool:
        return self._snap.services[self._SERVICE_NAME]["active"]

    @property
    def mysql_router_exporter_service_enabled(self) -> bool:
        return self._snap.services[self._EXPORTER_SERVICE_NAME]["active"]

    def update_mysql_router_service(self, *, enabled: bool, tls: bool = None) -> None:
        super().update_mysql_router_service(enabled=enabled, tls=tls)

        if tls:
            self._snap.set({"mysqlrouter.extra-options": f"--extra-config {self.tls_config_file}"})
        else:
            self._snap.unset("mysqlrouter.extra-options")

        router_is_running = self._snap.services[self._SERVICE_NAME]["active"]

        if enabled:
            if router_is_running:
                self._snap.restart([self._SERVICE_NAME])
            else:
                self._snap.start([self._SERVICE_NAME], enable=True)
        else:
            self._snap.stop([self._SERVICE_NAME], disable=True)

    def update_mysql_router_exporter_service(
        self,
        *,
        enabled: bool,
        config: "common.relations.cos.ExporterConfig" = None,
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
            self._snap.set({
                "mysqlrouter-exporter.listen-port": config.listen_port,
                "mysqlrouter-exporter.user": config.username,
                "mysqlrouter-exporter.password": config.password,
                "mysqlrouter-exporter.url": config.url,
                "mysqlrouter-exporter.service-name": self._unit_name.replace("/", "-"),
            })
            if tls:
                self._snap.set({
                    "mysqlrouter.tls-cacert-path": certificate_authority_filename,
                    "mysqlrouter.tls-cert-path": certificate_filename,
                    "mysqlrouter.tls-key-path": key_filename,
                })
            else:
                self._snap.unset("mysqlrouter.tls-cacert-path")
                self._snap.unset("mysqlrouter.tls-cert-path")
                self._snap.unset("mysqlrouter.tls-key-path")
            self._snap.start([self._EXPORTER_SERVICE_NAME], enable=True)
        else:
            self._snap.stop([self._EXPORTER_SERVICE_NAME], disable=True)
            self._snap.unset("mysqlrouter-exporter.listen-port")
            self._snap.unset("mysqlrouter-exporter.user")
            self._snap.unset("mysqlrouter-exporter.password")
            self._snap.unset("mysqlrouter-exporter.url")
            self._snap.unset("mysqlrouter-exporter.service-name")
            self._snap.unset("mysqlrouter.tls-cacert-path")
            self._snap.unset("mysqlrouter.tls-cert-path")
            self._snap.unset("mysqlrouter.tls-key-path")

    def install(
        self,
        *,
        unit: ops.Unit,
        model_uuid: str,
        snap_revision: str,
        refresh: charm_refresh.Machines,
    ) -> None:
        """Ensure snap is installed by this charm

        If snap is not installed, install it
        If snap is installed, check that it was installed by this charm & raise an exception otherwise

        Automatically retries if snap installation fails
        """
        unique_unit_name = f"{model_uuid}_{unit.name}"
        if self._snap.present:
            _raise_if_snap_installed_not_by_this_charm(unit=unit, model_uuid=model_uuid)
            return
        # Install snap
        logger.info(f"Installing snap revision {repr(snap_revision)}")
        unit.status = ops.MaintenanceStatus("Installing snap")

        def _set_retry_status(_) -> None:
            message = "Snap install failed. Retrying..."
            unit.status = ops.MaintenanceStatus(message)
            logger.debug(message)

        for attempt in tenacity.Retrying(
            stop=tenacity.stop_after_delay(60 * 5),
            wait=tenacity.wait_exponential(multiplier=10),
            retry=tenacity.retry_if_exception_type((snap_lib.SnapError, snap_lib.SnapAPIError)),
            after=_set_retry_status,
            reraise=True,
        ):
            with attempt:
                self._snap.ensure(state=snap_lib.SnapState.Present, revision=snap_revision)
        refresh.update_snap_revision()
        self._snap.hold()
        self._installed_by_unit.write_text(unique_unit_name)
        logger.debug(f"Wrote {unique_unit_name=} to {self._installed_by_unit.name=}")
        logger.info(f"Installed snap revision {repr(snap_revision)}")

    def refresh(
        self,
        *,
        unit: ops.Unit,
        model_uuid: str,
        snap_revision: str,
        refresh: charm_refresh.Machines,
    ) -> None:
        """Refresh snap

        If snap refresh fails and previous revision is still installed, raises `RefreshFailed`

        Does not automatically retry if snap installation fails
        """
        if not self._snap.present:
            self.install(
                unit=unit, model_uuid=model_uuid, snap_revision=snap_revision, refresh=refresh
            )
            return
        _raise_if_snap_installed_not_by_this_charm(unit=unit, model_uuid=model_uuid)

        revision_before_refresh = self._snap.revision
        if revision_before_refresh == snap_revision:
            raise ValueError(f"Cannot refresh snap; {snap_revision=} is already installed")

        logger.info(f"Refreshing snap to revision {repr(snap_revision)}")
        unit.status = ops.MaintenanceStatus("Refreshing snap")
        try:
            self._snap.ensure(state=snap_lib.SnapState.Present, revision=snap_revision)
        except (snap_lib.SnapError, snap_lib.SnapAPIError):
            logger.exception("Snap refresh failed")
            if self._snap.revision == revision_before_refresh:
                raise common.container.RefreshFailed
            else:
                refresh.update_snap_revision()
                raise
        else:
            refresh.update_snap_revision()
        logger.info(f"Refreshed snap to revision {repr(snap_revision)}")

    # TODO python3.10 min version: Use `list` instead of `typing.List`
    def _run_command(
        self,
        command: typing.List[str],
        *,
        timeout: typing.Optional[int] = 30,
        input: str = None,  # noqa: A002 Match subprocess.run()
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
            raise common.container.CalledProcessError(
                returncode=e.returncode, cmd=e.cmd, output=e.output, stderr=e.stderr
            )
        return output

    def path(self, *args, **kwargs) -> _Path:
        return _Path(*args, **kwargs)
