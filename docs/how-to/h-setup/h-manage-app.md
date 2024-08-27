# How to manage related applications

## Modern `mysql_client` interface:

Relations to new applications are supported via the "[mysql_client](https://github.com/canonical/charm-relation-interfaces/blob/main/interfaces/mysql_client/v0/README.md)" interface. To create a relation:

```shell
juju integrate mysql-router application
```

To remove a relation:

```shell
juju remove-relation mysql-router application
```

All listed on CharmHub applications are available [here](https://charmhub.io/mysql-router/integrations), e.g. [mysql-test-app](https://charmhub.io/mysql-test-app).

## Legacy `mysql-shared` interface:

This charm also supports the legacy relation via the `mysql` interface. Please note that these interface is deprecated.

 ```shell
juju relate mysql-router:shared-db myapplication
```

## Internal operator user

To rotate the internal router passwords, the relation with backend-database should be removed and related again. That process will generate a new user and password for the application, while retaining the requested database and data.

```shell
juju remove-relation mysql-router mysql

juju integrate mysql-router mysql
```