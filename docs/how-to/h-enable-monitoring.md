[note]
**Note**: All commands are written for [`juju >= v3.0`](https://juju.is/docs/juju/roadmap#heading--juju-3-0-0---22-oct-2022)
[/note]

# How to enable monitoring with COS and Grafana

This guide goes over the steps to integrate your MySQL Router deployment with COS to enable monitoring in Grafana.

To learn about Alert Rules, see [Charmed MySQL > How to enable COS Alert Rules](https://charmhub.io/mysql/docs/h-enable-alert-rules).

## Prerequisites
* Deployed [Charmed MySQL and Charmed MySQL Router](https://charmhub.io/mysql-router/docs/t-deploy-charm?channel=dpe/edge) operators
* A deployed [‘cos-lite’ bundle in a Kubernetes environment](https://charmhub.io/topics/canonical-observability-stack/tutorials/install-microk8s)

## Summary
* [Offer interfaces via the COS controller](#offer-interfaces-via-the-cos-controller)
* [Consume offers via the MySQL Router model](#consume-offers-via-the-mysql-router-model)
* [Deploy and integrate Grafana](#deploy-and-integrate-grafana)
* [Connect to the Grafana web interface](#connect-to-the-grafana-web-interface)

---

## Offer interfaces via the COS controller

First, we will switch to the COS K8s environment and offer COS interfaces to be cross-model integrated with the Charmed MySQLRouter VM model.

To switch to the Kubernetes controller for the COS model, run
```shell
juju switch <k8s_controller>:<cos_model_name>
```
To offer the COS interfaces, run
```shell
juju offer grafana:grafana-dashboard
juju offer loki:logging
juju offer prometheus:receive-remote-write
```

## Consume offers via the MySQL Router model

Next, we will switch to the Charmed MySQL Router model, find offers, and consume them.

We are currently on the Kubernetes controller for the COS model. To switch to the MySQL Router model, run

```shell
juju switch <machine_controller_name>:<mysql_router_model_name>
```
Display a list of available interfaces with the following command:
```
juju find-offers <k8s_controller>:  # Do not miss ':' here
```
In the sample output below, `k8s` is the k8s controller name and `cos` is the model where `cos-lite` has been deployed:

```shell
Store  URL               	Access  Interfaces
k8s	admin/cos.grafana 	admin   grafana_dashboard:grafana-dashboard
k8s	admin/cos.loki    	admin   loki_push_api:logging
k8s	admin/cos.prometheus  admin   prometheus_remote_write:receive-remote-write
```

To consume offers to be reachable in the current model, run

```shell
juju consume k8s:admin/cos.grafana
juju consume k8s:admin/cos.loki
juju consume k8s:admin/cos.prometheus
```

## Deploy and integrate Grafana

First, deploy [grafana-agent](https://charmhub.io/grafana-agent) and integrate it with the principal application for the subordinate MySQL Router app `<client_application>`: <!--TODO: Why not just use MySQL as example of principal? -->
```shell
juju deploy grafana-agent
juju integrate <client_application> grafana-agent
```

Integrate (previously known as "[relate](https://juju.is/docs/juju/integration)") `grafana-agent` with the COS interfaces:
```shell
juju integrate grafana-agent mysql-router:cos-agent
juju integrate grafana-agent grafana
juju integrate grafana-agent loki
juju integrate grafana-agent prometheus
```

After this is complete, Grafana will show the new dashboards `MySQLRouter Exporter` and allows access for Charmed MySQL Router logs on Loki.

Example of `juju status` on the Charmed MySQL Router VM model:

```shell
ubuntu@localhost:~$ juju status
Model 	Controller  Cloud/Region     	Version  SLA      	Timestamp
database  lxd     	localhost/localhost  3.1.8	unsupported  12:34:26Z

SAAS    	Status  Store  URL
grafana 	active  k8s	admin/cos.grafana
loki    	active  k8s	admin/cos.loki
prometheus  active  k8s	admin/cos.prometheus

App         	Version      	Status  Scale  Charm       	Channel 	Rev  Exposed  Message
grafana-agent                	active  	1  grafana-agent   stable   	65  no  	 
mysql       	8.0.34-0ubun...  active  	1  mysql       	8.0/stable  196  no  	 
mysql-router	8.0.36-0ubun...  active  	1  mysql-router	dpe/edge	153  no  	 
mysql-test-app  0.0.2        	active  	1  mysql-test-app  stable   	36  no  	 

Unit            	Workload  Agent  Machine  Public address  Ports       	Message
mysql-test-app/0*   active	idle   1    	10.205.193.82              	 
  grafana-agent/0*  active	idle        	10.205.193.82              	 
  mysql-router/0*   active	idle        	10.205.193.82              	 
mysql/0*        	active	idle   0    	10.205.193.13   3306,33060/tcp  Primary

Machine  State	Address    	Inst id    	Base      	AZ  Message
0    	started  10.205.193.13  juju-65afbd-0  ubuntu@22.04  	Running
1    	started  10.205.193.82  juju-65afbd-1  ubuntu@22.04  	Running
```

Example of `juju status` on the COS K8s model:

```shell
ubuntu@localhost:~$ juju status
Model  Controller  Cloud/Region    	Version  SLA      	Timestamp
cos	k8s     	microk8s/localhost  3.1.8	unsupported  20:29:12Z

App       	Version  Status  Scale  Charm         	Channel  Rev  Address     	Exposed  Message
alertmanager  0.27.0   active  	1  alertmanager-k8s  stable   106  10.152.183.197  no  	 
catalogue          	active  	1  catalogue-k8s 	stable	33  10.152.183.38   no  	 
grafana   	9.5.3	active  	1  grafana-k8s   	stable   106  10.152.183.238  no  	 
loki      	2.9.4	active  	1  loki-k8s      	stable   124  10.152.183.84   no  	 
prometheus	2.49.1   active  	1  prometheus-k8s	stable   171  10.152.183.182  no  	 
```
## Connect to Grafana web interface

To connect to the Grafana web interface, follow the [Browse dashboards](https://charmhub.io/topics/canonical-observability-stack/tutorials/install-microk8s?_ga=2.201254254.1948444620.1704703837-757109492.1701777558#heading--browse-dashboards) section of the MicroK8s "Getting started" guide.

```shell
juju run grafana/leader get-admin-password --model <k8s_controller>:<cos_model_name>
```