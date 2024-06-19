# How to enable encryption

MySQL Router is a subordinated charm, client applications connects it using local UNIX socket, therefor TLS encryption is not necessary between client application and MySQL Router.

The TLS encryption is recommended between MySQL Router and MySQL server. To enable it follow the [dedicated manual](https://charmhub.io/mysql/docs/t-enable-security).