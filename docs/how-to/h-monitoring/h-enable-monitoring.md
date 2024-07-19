# Enable monitoring

> **:information_source: Hint**: Use [Juju 3](/t/5064). Otherwise replace `juju run ...` with `juju run-action --wait ...` and `juju integrate` with `juju relate` for Juju 2.9

Enabling monitoring requires that you:
* [Have a Charmed MySQL and Charmed MySQLRouter deployed](https://charmhub.io/mysql-router/docs/t-deploy-charm?channel=dpe/edge)
* [Deploy ‘cos-lite’ bundle in a Kubernetes environment](https://charmhub.io/topics/canonical-observability-stack/tutorials/install-microk8s)

Switch to the COS K8s environment and offer COS interfaces to be cross-model integrated (related) with Charmed MySQLRouter VM model:

```shell
# Switch to the Kubernetes controller, in particular the COS model
juju switch <k8s_controller>:<cos_model_name>

juju offer grafana:grafana-dashboard
juju offer loki:logging
juju offer prometheus:receive-remote-write
```

 Switch to the Charmed MySQLRouter VM model, find offers and integrate (relate) with them:

```shell
# We are on the Kubernetes controller, for the COS model. Switch to the MySQLRouter model
juju switch <machine_controller_name>:<mysql_router_model_name>

juju find-offers <k8s_controller>:  # Do not miss ':' here
```

A similar output should appear, if `k8s` is the k8s controller name and `cos` is the model where cos-lite has been deployed:

```shell
Store  URL               	Access  Interfaces
k8s	admin/cos.grafana 	admin   grafana_dashboard:grafana-dashboard
k8s	admin/cos.loki    	admin   loki_push_api:logging
k8s	admin/cos.prometheus  admin   prometheus_remote_write:receive-remote-write
```

Consume offers to be reachable in the current model:

```shell
juju consume k8s:admin/cos.grafana
juju consume k8s:admin/cos.loki
juju consume k8s:admin/cos.prometheus
```

Now deploy ‘[grafana_agent](https://charmhub.io/grafana-agent)’ (subordinate charm) alongside the Charmed MySQL Router application (also subordinate) and integrate (relate) it with Charmed MySQLRouter, then later integrate (relate) `grafana-agent `with the consumed COS offers:

```shell
# Assume <client_application> is the principal application for the subordinate mysql router application
juju deploy grafana-agent
juju integrate <client_application> grafana-agent
juju integrate grafana-agent mysql-router:cos-agent
juju integrate grafana-agent grafana
juju integrate grafana-agent loki
juju integrate grafana-agent prometheus
```

After this is complete, Grafana will show the new dashboards `MySQLRouter Exporter` and allows access for Charmed MySQLRouter logs on Loki.

An example of `juju status` on the Charmed MySQLRouter VM model:

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

To connect to the Grafana WEB interface, follow the COS section “[Browse dashboards](https://charmhub.io/topics/canonical-observability-stack/tutorials/install-microk8s#heading--browse-dashboards)”:

```shell
juju run grafana/leader get-admin-password --model <k8s_controller>:<cos_model_name>
```