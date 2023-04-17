# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""File containing constants to be used in the charm."""

CHARMED_MYSQL_SNAP = "charmed-mysql"
CHARMED_MYSQL_SNAP_REVISION = 45
SNAP_DAEMON_USER = "snap_daemon"
CHARMED_MYSQL_COMMON_DIRECTORY = "/var/snap/charmed-mysql/common"
CHARMED_MYSQL_ROUTER = "charmed-mysql.mysqlrouter"
CHARMED_MYSQL_ROUTER_SERVICE = "mysqlrouter-service"
PEER = "mysql-router-peers"
DATABASE_REQUIRES_RELATION = "backend-database"
DATABASE_PROVIDES_RELATION = "database"
MYSQL_ROUTER_LEADER_BOOTSTRAPED = "mysql-router-leader-bootstraped"
MYSQL_ROUTER_REQUIRES_DATA = "requires-database-data"
MYSQL_ROUTER_PROVIDES_DATA = "provides-database-data"
PASSWORD_LENGTH = 24
# Constants for legacy relations
LEGACY_SHARED_DB = "shared-db"
LEGACY_SHARED_DB_DATA = "shared-db-data"
LEGACY_SHARED_DB_DATA_FORWARDED = "shared-db-data-forwarded"
