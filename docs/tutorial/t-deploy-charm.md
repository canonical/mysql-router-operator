# Get a MySQL Router up and running

This is part of the [MySQL Router Tutorial](/t/12332). Please refer to this page for more information and the overview of the content. The following document will deploy "MySQL Router" together with "MySQL server" (coming from the separate charm "[Charmed MySQL](https://charmhub.io/mysql)"). 

## Deploy Charmed MySQL + MySQL Router

To deploy Charmed MySQL + MySQL Router, all you need to do is run the following commands:

```shell
juju deploy mysql --channel 8.0
juju deploy mysql-router --channel dpe/edge
```
Juju will now fetch charms from [Charmhub](https://charmhub.io/) and begin deploying it to the LXD VMs. This process can take several minutes depending on how provisioned (RAM, CPU, etc) your machine is. You can track the progress by running:
```shell
juju status --watch 1s
```

This command is useful for checking the status of Juju applications and gathering information about the machines hosting them. Some of the helpful information it displays include IP addresses, ports, state, etc. The command updates the status of charms every second and as the application starts you can watch the status and messages of their change. Wait until the application is ready - when it is ready, `juju status` will show:
```shell
TODO
```
> :tipping_hand_man: **Tip**: To exit the screen with `juju status --watch 1s`, enter `Ctrl+c`.
If you want to further inspect juju logs, can watch for logs with `juju debug-log`.
More info on logging at [juju logs](https://juju.is/docs/olm/juju-logs).

At this stage MySQL Router will stay in blocked state due to missing relation/integration with MySQL DB, let's integrate them:
```shell
juju integrate mysql mysql-router
```
Shortly the `juju status` will report new blocking reason `Missing relation: database` as it waits for a client to consume DB service, let's deploy [data-integrator](https://charmhub.io/data-integrator) and request access to database `test123`:
```shell
juju deploy data-integrator --config database-name=test123
juju relate data-integrator mysql-router
```
In couple of seconds, the status will be happy for entire model:
```shell
TODO
```

## Access database

The first action most users take after installing MySQL is accessing MySQL. The easiest way to do this is via the [MySQL Command-Line Client](https://dev.mysql.com/doc/refman/8.0/en/mysql.html) `mysql`. Connecting to the database requires that you know the values for `host`, `username` and `password`. To retrieve the necessary fields please run data-integrator action `get-credentials`:
```shell
juju run data-integrator/leader get-credentials
```
Running the command should output:
```yaml
TODO
```

The host’s IP address can be found with `juju status` (the application hosting the MySQL Router application):
```shell
...
TODO
...
```

To access the MySQL database via MySQL Router choose read-write (port 6446) or read-only (port 6447) endpoints:
```shell
mysql -h 10.152.183.52 -P6446 -urelation-4-6 -pNu7wK85QU7dpVX66X56lozji test123
```

Inside MySQL list DBs available on the host `show databases`:
```shell
mysql> show databases;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| performance_schema |
| test123            |
+--------------------+
3 rows in set (0.00 sec)

```
> :tipping_hand_man: **Tip**: if at any point you'd like to leave the MySQL client, enter `Ctrl+d` or type `exit`.

You can now interact with MySQL directly using any [MySQL Queries](https://dev.mysql.com/doc/refman/8.0/en/entering-queries.html). For example entering `SELECT VERSION(), CURRENT_DATE;` should output something like:
```shell
mysql> SELECT VERSION(), CURRENT_DATE;
+-------------------------+--------------+
| VERSION()               | CURRENT_DATE |
+-------------------------+--------------+
| 8.0.34-0ubuntu0.22.04.1 | 2023-10-17    |
+-------------------------+--------------+
1 row in set (0.00 sec)
```

Feel free to test out any other MySQL queries. When you’re ready to leave the MySQL shell you can just type `exit`. Now you will be in your original shell where you first started the tutorial; here you can interact with Juju and LXD.

### Remove the user

To remove the user, remove the relation. Removing the relation automatically removes the user that was created when the relation was created. Enter the following to remove the relation:
```shell
juju remove-relation mysql-router data-integrator
```

Now try again to connect to the same MySQL Router you just used above:
```shell
mysql -h 10.152.183.52 -P6446 -urelation-4-6 -pNu7wK85QU7dpVX66X56lozji test123
```

This will output an error message:
```shell
ERROR 1045 (28000): Access denied for user 'relation-4-6'@'mysql-router-1.mysql-router-endpoints.tutorial.svc.clust' (using password: YES)
```
As this user no longer exists. This is expected as `juju remove-relation mysql-router data-integrator` also removes the user.
Note: data stay remain on the server at this stage!

Relate the the two applications again if you wanted to recreate the user:
```shell
juju relate data-integrator mysql-router
```
Re-relating generates a new user and password:
```shell
juju run data-integrator/leader get-credentials
```
You can connect to the database with this new credentials.
From here you will see all of your data is still present in the database.