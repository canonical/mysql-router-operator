# Interfaces/endpoints

MySQL Router supports modern ['mysql_client'](https://github.com/canonical/charm-relation-interfaces) interface. Applications can easily connect MySQL using ['data_interfaces'](https://charmhub.io/data-platform-libs/libraries/data_interfaces) library from ['data-platform-libs'](https://github.com/canonical/data-platform-libs/).

### Modern `mysql_client` interface (`database` endpoint):

Adding a relation is accomplished with `juju relate` (or `juju integrate` for Juju 3.x) via endpoint `database`. Read more about [Juju relations (integrations)](https://juju.is/docs/olm/relations). Example:

```shell
# Deploy Charmed MySQL and MySQL Router clusters
juju deploy mysql -n 3
juju deploy mysql-router -n 3 --channel dpe/edge

# Deploy the relevant charms, e.g. mysql-test-app
juju deploy mysql-test-app

# Relate all applications
juju integrate mysql mysql-router
juju integrate mysql-router:database mysql-test-app

# Check established relation (using mysql_client interface):
juju status --relations

# Example of the properly established relation:
# > Integration provider        Requirer                         Interface           Type     Message
# > mysql:database              mysql-router:backend-database    mysql_client        regular
# > mysql-router:database       mysql-test-app:database          mysql_client        regular         
# > ...
```

**Note:** In order to relate with Charmed MySQL, every table created by the client application must have a primary key. This is required by the [group replication plugin](https://dev.mysql.com/doc/refman/8.0/en/group-replication-requirements.html) enabled in this charm.

See all the charm interfaces [here](https://charmhub.io/mysql-router/integrations).