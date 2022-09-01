# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""File containing constants to be used in the charm."""

MYSQL_ROUTER_APT_PACKAGE = "mysql-router"
MYSQL_ROUTER_GROUP = "mysql"
MYSQL_ROUTER_USER = "mysql"
MYSQL_HOME_DIRECTORY = "/var/lib/mysql"
PEER = "mysql-router"
DATABASE_REQUIRES_RELATION = "database"
MYSQL_ROUTER_BOOTSTRAPED = "mysql-router-bootstraped"
MYSQL_ROUTER_UNIT_TEMPLATE = "templates/mysqlrouter.service.j2"
MYSQL_ROUTER_SERVICE_NAME = "mysqlrouter.service"
MYSQL_ROUTER_SYSTEMD_DIRECTORY = "/etc/systemd/system"
MYSQL_ROUTER_DATABASE_DATA = "database-data"
PASSWORD_LENGTH = 24
# Constants for legacy relations
LEGACY_SHARED_DB = "shared-db"
LEGACY_SHARED_DB_DATA = "shared-db-data"
LEGACY_SHARED_DB_DATA_FORWARDED = "shared-db-data-forwarded"
