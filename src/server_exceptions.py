# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""MySQL Server unreachable or unhealthy"""

import ops

import status_exception


class Error(status_exception.StatusException):
    """MySQL Server unreachable or unhealthy"""


class ConnectionError(Error):
    """MySQL Server unreachable

    MySQL client error 2003
    https://dev.mysql.com/doc/mysql-errors/8.0/en/client-error-reference.html#error_cr_conn_host_error
    """

    MESSAGE = "Failed to connect to MySQL Server. Will retry next Juju event"

    def __init__(self):
        super().__init__(ops.WaitingStatus(self.MESSAGE))
