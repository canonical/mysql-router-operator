[note]
**Note**: All commands are written for `juju >= v3.1`

If you're using `juju 2.9`, check the [`juju 3.0` Release Notes](https://juju.is/docs/juju/roadmap#heading--juju-3-0-0---22-oct-2022).
[/note]

# Enable tracing
This guide contains the steps to enable tracing with [Grafana Tempo](https://grafana.com/docs/tempo/latest/) for your MySQL Router application. 

To summarize:
* [Deploy the Tempo charm in a COS K8s environment](#heading--deploy)
* [Integrate it with the COS charms](#heading--integrate)
* [Offer interfaces for cross-model integrations](#heading--offer)
* [View MySQLRouter traces on Grafana](#heading--view)


[note type="caution"]
**Warning:** This is feature is in development. It is **not recommended** for production environments. 

This feature is available for Charmed MySQL Router revision 208+ only.
[/note]

## Prerequisites
Enabling tracing with Tempo requires that you:
- Have deployed a Charmed MySQL application
  - See [How to manage MySQL units](https://discourse.charmhub.io/t/charmed-mysql-how-to-manage-units/9904)
- Have deployed a Charmed MySQL Router application in the same model as the Charmed MySQL application
  - See [How to manage MySQL Router units](https://discourse.charmhub.io/t/mysql-router-how-to-manage-units/12338)
- Have deployed a 'cos-lite' bundle from the `latest/edge` track in a Kubernetes environment
  - See [Getting started on MicroK8s](https://charmhub.io/topics/canonical-observability-stack/tutorials/install-microk8s)

---
<a href="#heading--deploy"><h2 id="heading--deploy"> Deploy Tempo </h2></a>


First, switch to the Kubernetes controller where the COS model is deployed:

```shell
juju switch <k8s_controller_name>:<cos_model_name>
```
Then, deploy the [`tempo-k8s`](https://charmhub.io/tempo-k8s) charm:
```shell
juju deploy -n 1 tempo-k8s --channel latest/edge
```

<a href="#heading--integrate"><h2 id="heading--integrate"> Integrate with the COS charms </h2></a>

Integrate `tempo-k8s` with the COS charms as follows:

```shell
juju integrate tempo-k8s:grafana-dashboard grafana:grafana-dashboard
juju integrate tempo-k8s:grafana-source grafana:grafana-source
juju integrate tempo-k8s:ingress traefik:traefik-route
juju integrate tempo-k8s:metrics-endpoint prometheus:metrics-endpoint
juju integrate tempo-k8s:logging loki:logging
```
If you would like to instrument traces from the COS charms as well, create the following integrations:
```shell
juju integrate tempo-k8s:tracing alertmanager:tracing
juju integrate tempo-k8s:tracing catalogue:tracing
juju integrate tempo-k8s:tracing grafana:tracing
juju integrate tempo-k8s:tracing loki:tracing
juju integrate tempo-k8s:tracing prometheus:tracing
juju integrate tempo-k8s:tracing traefik:tracing
```

<a href="#heading--offer"><h2 id="heading--offer"> Offer interfaces </h2></a>

Next, offer interfaces for cross-model integrations from the model where Charmed MySQL Router is deployed.

To offer the Tempo integration, run

```shell
juju offer tempo-k8s:tracing
```

Then, switch to the Charmed MySQL Router model, find the offers, and integrate (relate) with them:

```shell
juju switch <machine_controller_name>:<mysql_router_model_name>

juju find-offers <k8s_controller_name>:  
```
> :exclamation: Do not miss the "`:`" in the command above.

Below is a sample output where `k8s` is the K8s controller name and `cos` is the model where `cos-lite` and `tempo-k8s` are deployed:

```shell
Store  URL                            Access  Interfaces
k8s    admin/cos.tempo-k8s            admin   tracing:tracing
```

Next, consume this offer so that it is reachable from the current model:

```shell
juju consume k8s:admin/cos.tempo-k8s
```

Relate Charmed MySQL Router with the above consumed interface:

```shell
juju integrate mysql-router:tracing tempo-k8s:tracing
```

Wait until the model settles. The following is an example of the `juju status --relations` on the Charmed MySQL Router model:

```shell
Model     Controller  Cloud/Region         Version  SLA          Timestamp
database  lxd         localhost/localhost  3.4.3    unsupported  12:48:46Z

SAAS       Status  Store  URL
tempo-k8s  active  uk8s   admin/cos.tempo-k8s

App             Version          Status  Scale  Charm           Channel      Rev  Exposed  Message
mysql           8.0.37-0ubun...  active      1  mysql           8.0/edge     253  no       
mysql-router    8.0.37-0ubun...  active      1  mysql-router    dpe/edge     216  no       
mysql-test-app  0.0.2            active      1  mysql-test-app  latest/edge   46  no       Last written value=54713

Unit               Workload  Agent  Machine  Public address  Ports           Message
mysql-test-app/0*  active    idle   1        10.205.193.43                   Last written value=54713
  mysql-router/0*  active    idle            10.205.193.43                   
mysql/0*           active    idle   0        10.205.193.72   3306,33060/tcp  Primary

Machine  State    Address        Inst id        Base          AZ  Message
0        started  10.205.193.72  juju-7f1fdf-0  ubuntu@22.04      Running
1        started  10.205.193.43  juju-7f1fdf-1  ubuntu@22.04      Running

Integration provider                           Requirer                                       Interface                    Type         Message
mysql-router:cos                               mysql-router:cos                               cos                          peer         
mysql-router:database                          mysql-test-app:database                        mysql_client                 subordinate  
mysql-router:deprecated-shared-db-credentials  mysql-router:deprecated-shared-db-credentials  _deprecated_shared_db_peers  peer         
mysql-router:tls                               mysql-router:tls                               tls                          peer         
mysql-router:upgrade-version-a                 mysql-router:upgrade-version-a                 upgrade                      peer         
mysql-test-app:application-peers               mysql-test-app:application-peers               application-peers            peer         
mysql:database                                 mysql-router:backend-database                  mysql_client                 regular      
mysql:database-peers                           mysql:database-peers                           mysql_peers                  peer         
mysql:restart                                  mysql:restart                                  rolling_op                   peer         
mysql:upgrade                                  mysql:upgrade                                  upgrade                      peer         
tempo-k8s:tracing                              mysql-router:tracing                           tracing                      regular 
```

[note]
**Note:** All traces are exported to Tempo using HTTP. Support for sending traces via HTTPS is an upcoming feature.
[/note]

<a href="#heading--view"><h2 id="heading--view"> View traces </h2></a>

After this is complete, the Tempo traces will be accessible from Grafana under the `Explore` section with `tempo-k8s` as the data source. You will be able to select `mysql-router` as the `Service Name` under the `Search` tab to view traces belonging to Charmed MySQL Router.

Below is a screenshot demonstrating a Charmed MySQL Router trace:
![Example MySQL Router trace with Grafana Tempo|690x382](upload://iXdGsc3ACrhMal43QwNU5q5OCJ7.jpeg)


Feel free to read through the [Tempo documentation](https://discourse.charmhub.io/t/tempo-k8s-docs-index/14005) at your leisure to explore its deployment and its integrations.