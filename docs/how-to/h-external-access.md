# Optimal MySQL Router Setup

For optimal performance, it is recommended that [MySQL Router](https://dev.mysql.com/doc/mysql-router/8.0/en/) is run alongside your application and that your application uses a Unix domain socket to connect to and execute queries against MySQL Router. The usage of a Unix domain socket here results in increased network performance due to the reduced network hops and in increased security due to the lack of exposed ports.

When your application implements the modern (preferred) interface in  [MySQL Router's supported interfaces](https://discourse.charmhub.io/t/mysql-router-how-to-manage-app/12339) , the MySQL Router charm is deployed as a subordinate of your application charm and your application will be presented with a Unix domain socket, over the interface, to connect to MySQL Router.

## Accessing MySQL Router outside of Juju

A known limitation of relating with MySQL Router (a subordinate charm) is that your application would need to be deployed as a Juju application. However, if your application exists outside of the Juju ecosystem, you can access MySQL Router externally with the [Data Integrator](https://charmhub.io/data-integrator) charm.

### Example setup
The steps below show you how to deploy and set up MySQL, MySQL Router, and Data Integrator for access outside of Juju.

First, deploy all the charms:
```shell
juju deploy mysql --channel 8.0/edge --trust
juju deploy data-integrator --config database-name=test_database
juju deploy mysql-router --channel dpe/edge
```
> Feel free to change `test_database` to your name of choice

Integrate:
* `mysql` with `mysql-router`
* `data-integrator` with `mysql-router`, since in this case we want to generate the credentials to access MySQL Router 

```shell
juju integrate mysql mysql-router
juju integrate data-integrator mysql-router
```

The following is a sample output of the `get-credentials` action run on a `data-integrator` unit:
```shell
juju run data-integrator/leader get-credentials
```

```shell
Running operation 1 with 1 task
  - task 2 on unit-data-integrator-0

Waiting for task 2...
mysql:
  data: '{"database": "test_database", "external-node-connectivity": "true", "requested-secrets":
	"[\"username\", \"password\", \"tls\", \"tls-ca\", \"uris\"]"}'
  database: test_database
  endpoints: 10.205.193.235:6446
  password: mysupersecuredatabasepassword
  read-only-endpoints: 10.205.193.235:6447
  username: relation-9-8
ok: "True"
```

You can then connect to MySQL Router with the provided `endpoints` from your application that resides outside of Juju.

## Using a Virtual IP to connect to MySQL Router

If the MySQL Router charm is related to the Data Integrator charm, it is possible for a user to configure MySQL Router to use a certain Virtual IP. This assumes that the user has somehow ensured that the Virtual IP resolves to the node on which the MySQL Router charm is deployed.

To configure the MySQL Router charm with a virtual IP, run
```shell
juju config mysql-router/0 vip=<your_virtual_ip>
```

### Integrate with HACluster

Alternatively, you can integrate with the [HACluster charm](https://charmhub.io/hacluster) if you would like a Virtual IP that is generated and maintained for you.

HACluster is a collection of solutions by [ClusterLabs](https://clusterlabs.org/) designed to create and manage resources. The creation of resources like Virtual IPs is handled by [Pacemaker](https://clusterlabs.org/pacemaker/), whereas the management of these resources is handled by [Corosync](https://clusterlabs.org/corosync.html). 

Pacemaker will create and attach a Virtual IP to one of your Data Integrator nodes (that is related to MySQL Router), while Corosync will ensure automatic failover if the node with the Virtual IP faces connectivity or other issues. **This setup requires at least 3 Data Integrator nodes, each related to both MySQL Router and HACluster.**

[note type="warning"]
**Warning**: The Virtual IP supplied to MySQL Router should be in the same subnet as the nodes on which the MySQL Router charm is running. Else, you may encounter unexpected behavior from the HACluster charm when it tries to create the Virtual IP.
[/note]

#### Example setup
The steps below show you how to deploy and set up MySQL, MySQL Router, Data Integrator, and HACluster.

First, deploy all the charms
```shell
juju deploy mysql --channel 8.0/edge --trust
juju deploy -n 3 data-integrator --config database-name=test_database
juju deploy mysql-router --channel dpe/edge
juju deploy hacluster
```
> Note that the `data-integrator` requires a minimum of 3 nodes for this HACluster setup to work

Configure the VIP on `mysql-router`. Please ensure that the VIP is in an accessible subnet:
```shell
juju config mysql-router vip=10.205.193.35
```

Then, integrate:
* `mysql-router` with `mysql`
* `mysql-router` and `hacluster` with `data-integrator`
* `mysql-router` with `hacluster`

```
juju integrate mysql-router mysql

juju integrate data-integrator mysql-router
juju integrate data-integrator:juju-info hacluster:juju-info

juju integrate mysql-router hacluster
```

The following is a sample output of the `get-credentials` action run on a `data-integrator` unit:
```shell
juju run data-integrator/leader get-credentials
```
```shell
Running operation 1 with 1 task
  - task 2 on unit-data-integrator-0

Waiting for task 2...
mysql:
  data: '{"database": "test_database", "external-node-connectivity": "true", "requested-secrets":
	"[\"username\", \"password\", \"tls\", \"tls-ca\", \"uris\"]"}'
  database: test_database
  endpoints: 10.205.193.35:6446
  password: mysupersecuredatabasepassword
  read-only-endpoints: 10.205.193.35:6447
  username: relation-12_cf668cc3521149-9
ok: "True"

```