# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest

import workload


@pytest.mark.parametrize(
    "config_file_text,username",
    [
        (
            """[DEFAULT]
name = system
keyring_path = /var/snap/charmed-mysql/64/var/lib/mysqlrouter/keyring
master_key_path = /var/snap/charmed-mysql/64/etc/mysqlrouter/mysqlrouter.key
connect_timeout = 5
read_timeout = 30
dynamic_state = /var/snap/charmed-mysql/64/var/lib/mysqlrouter/state.json
client_ssl_cert = /var/snap/charmed-mysql/64/var/lib/mysqlrouter/router-cert.pem
client_ssl_key = /var/snap/charmed-mysql/64/var/lib/mysqlrouter/router-key.pem
client_ssl_mode = PREFERRED
server_ssl_mode = PREFERRED
server_ssl_verify = DISABLED
unknown_config_option = error

[logger]
level = INFO

[metadata_cache:bootstrap]
cluster_type = gr
router_id = 1
user = mysql_router1_hc3hpayqp2by
ttl = 5
auth_cache_ttl = -1
auth_cache_refresh_interval = 5
use_gr_notifications = 1

[routing:bootstrap_rw]
bind_address = 127.0.0.1
bind_port = 6446
socket = /var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock
destinations = metadata-cache://cluster-set-35f57988bc107ceafce1854a03664d6b/?role=PRIMARY
routing_strategy = first-available
protocol = classic

[routing:bootstrap_ro]
bind_address = 127.0.0.1
bind_port = 6447
socket = /var/snap/charmed-mysql/common/run/mysqlrouter/mysqlro.sock
destinations = metadata-cache://cluster-set-35f57988bc107ceafce1854a03664d6b/?role=SECONDARY
routing_strategy = round-robin-with-fallback
protocol = classic

[routing:bootstrap_x_rw]
bind_address = 127.0.0.1
bind_port = 6448
socket = /var/snap/charmed-mysql/common/run/mysqlrouter/mysqlx.sock
destinations = metadata-cache://cluster-set-35f57988bc107ceafce1854a03664d6b/?role=PRIMARY
routing_strategy = first-available
protocol = x

[routing:bootstrap_x_ro]
bind_address = 127.0.0.1
bind_port = 6449
socket = /var/snap/charmed-mysql/common/run/mysqlrouter/mysqlxro.sock
destinations = metadata-cache://cluster-set-35f57988bc107ceafce1854a03664d6b/?role=SECONDARY
routing_strategy = round-robin-with-fallback
protocol = x

[http_server]
port = 8443
ssl = 1
ssl_cert = /var/snap/charmed-mysql/64/var/lib/mysqlrouter/router-cert.pem
ssl_key = /var/snap/charmed-mysql/64/var/lib/mysqlrouter/router-key.pem
bind_address = 127.0.0.1

[http_auth_realm:default_auth_realm]
backend = default_auth_backend
method = basic
name = default_realm

[rest_router]
require_realm = default_auth_realm

[rest_api]

[http_auth_backend:default_auth_backend]
backend = metadata_cache

[rest_routing]
require_realm = default_auth_realm

[rest_metadata_cache]
require_realm = default_auth_realm

""",
            "mysql_router1_hc3hpayqp2by",
        ),
        (
            """# File automatically generated during MySQL Router bootstrap
[DEFAULT]
name=system
keyring_path=/var/lib/mysqlrouter/keyring
master_key_path=/etc/mysqlrouter/mysqlrouter.key
connect_timeout=5
read_timeout=30
dynamic_state=/var/lib/mysqlrouter/state.json
client_ssl_cert=/var/lib/mysqlrouter/router-cert.pem
client_ssl_key=/var/lib/mysqlrouter/router-key.pem
client_ssl_mode=PREFERRED
server_ssl_mode=AS_CLIENT
server_ssl_verify=DISABLED
unknown_config_option=error

[logger]
level=INFO

[metadata_cache:bootstrap]
cluster_type=gr
router_id=1
user=mysql_router1_t0kj7qvusegl
ttl=5
auth_cache_ttl=-1
auth_cache_refresh_interval=5
use_gr_notifications=1

[routing:bootstrap_rw]
bind_address=0.0.0.0
bind_port=6446
destinations=metadata-cache://cluster-set-2137eca38547ab65bdaecb2833dedaf3/?role=PRIMARY
routing_strategy=first-available
protocol=classic

[routing:bootstrap_ro]
bind_address=0.0.0.0
bind_port=6447
destinations=metadata-cache://cluster-set-2137eca38547ab65bdaecb2833dedaf3/?role=SECONDARY
routing_strategy=round-robin-with-fallback
protocol=classic

[routing:bootstrap_x_rw]
bind_address=0.0.0.0
bind_port=6448
destinations=metadata-cache://cluster-set-2137eca38547ab65bdaecb2833dedaf3/?role=PRIMARY
routing_strategy=first-available
protocol=x

[routing:bootstrap_x_ro]
bind_address=0.0.0.0
bind_port=6449
destinations=metadata-cache://cluster-set-2137eca38547ab65bdaecb2833dedaf3/?role=SECONDARY
routing_strategy=round-robin-with-fallback
protocol=x

[http_server]
port=8443
ssl=1
ssl_cert=/var/lib/mysqlrouter/router-cert.pem
ssl_key=/var/lib/mysqlrouter/router-key.pem
bind_address=127.0.0.1

[http_auth_realm:default_auth_realm]
backend=default_auth_backend
method=basic
name=default_realm

[rest_router]
require_realm=default_auth_realm

[rest_api]

[http_auth_backend:default_auth_backend]
backend=metadata_cache

[rest_routing]
require_realm=default_auth_realm

[rest_metadata_cache]
require_realm=default_auth_realm

""",
            "mysql_router1_t0kj7qvusegl",
        ),
    ],
)
def test_parse_username_from_config(config_file_text, username):
    assert workload.RunningWorkload._parse_username_from_config(config_file_text) == username
