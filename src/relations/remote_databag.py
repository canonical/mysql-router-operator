# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation databag for remote application"""

import logging
import typing

import charms.data_platform_libs.v0.data_interfaces as data_interfaces
import ops

import status_exception

logger = logging.getLogger(__name__)


class IncompleteDatabag(status_exception.StatusException):
    """Databag is missing required key"""

    def __init__(self, *, app_name: str, endpoint_name: str) -> None:
        super().__init__(
            ops.WaitingStatus(f"Waiting for {app_name} app on {endpoint_name} endpoint")
        )


class RemoteDatabag(dict):
    """Relation databag for remote application"""

    def __init__(
        self,
        # TODO python3.10 min version: Use `|` instead of `typing.Union`
        interface: typing.Union[
            data_interfaces.DatabaseRequires, data_interfaces.DatabaseProvides
        ],
        relation: ops.Relation,
    ) -> None:
        super().__init__(interface.fetch_relation_data()[relation.id])
        self._app_name = relation.app.name
        self._endpoint_name = relation.name

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            logger.debug(
                f"Required {key=} missing from databag for {self._app_name=} on {self._endpoint_name=}"
            )
            raise IncompleteDatabag(app_name=self._app_name, endpoint_name=self._endpoint_name)
