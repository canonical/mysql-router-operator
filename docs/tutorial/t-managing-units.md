# Scale your MySQL Router

This is part of the [Charmed MySQL Tutorial](/t/12176). Please refer to this page for more information and the overview of the content.

## Adding and Removing units

Please check the explanation of scaling Charmed MySQL operator [here](https://charmhub.io/mysql/docs/t-managing-units).

### Add more mysql-router instances
You can add two more units to your deployed MySQL Router application by scaling it to three units using:
```shell
juju scale-application mysql-router 3
```

You can now watch the scaling process in live using: `juju status --watch 1s`. It usually takes several minutes for new cluster members to be added. You’ll know that all three nodes are in sync when `juju status` reports `Workload=active` and `Agent=idle`:
```shell
Model     Controller  Cloud/Region        Version  SLA          Timestamp
tutorial  overlord    microk8s/localhost  3.4.3    unsupported  22:48:57+01:00

App               Version  Status  Scale  Charm             Channel   Rev  Address         Exposed  Message
data-integrator            active      1  data-integrator   stable     13  10.152.183.142  no       
mysql             8.4.7    active      1  mysql             8.4/edge  109  10.152.183.68   no       
mysql-router      8.4.7    active      3  mysql-router      8.4/edge   68  10.152.183.52   no       

Unit                 Workload  Agent  Address     Ports  Message
data-integrator/0*   active    idle   10.1.12.3          
mysql/0*             active    idle   10.1.12.36         Primary
mysql-router/0*      active    idle   10.1.12.14         
mysql-router/1       active    idle   10.1.12.32         
mysql-router/2       active    idle   10.1.12.31  
```

The same way you can scale Charmed MySQL:
```shell
juju scale-application mysql 3
```
Make sure all units are active (using `juju status`):
```shell
App               Version  Status  Scale  Charm             Channel   Rev  Address         Exposed  Message
data-integrator            active      1  data-integrator   stable     13  10.152.183.142  no       
mysql             8.4.7    active      3  mysql             8.4/edge  109  10.152.183.68   no       
mysql-router      8.4.7    active      3  mysql-router      8.4/edge   68  10.152.183.52   no       

Unit                 Workload  Agent  Address     Ports  Message
data-integrator/0*   active    idle   10.1.12.3          
mysql/0*             active    idle   10.1.12.36         Primary
mysql/1              active    idle   10.1.12.34         
mysql/2              active    idle   10.1.12.43         
mysql-router/0*      active    idle   10.1.12.14         
mysql-router/1       active    idle   10.1.12.32         
mysql-router/2       active    idle   10.1.12.31  
```

### Remove extra members
Removing a unit from the application, scales the replicas down.
```shell
juju scale-application mysql-router 2
juju scale-application mysql 2
```

You’ll know that the replica was successfully removed when `juju status --watch 1s` reports:
```shell
Model     Controller  Cloud/Region        Version  SLA          Timestamp
tutorial  overlord    microk8s/localhost  3.4.3    unsupported  22:48:57+01:00

App               Version  Status  Scale  Charm             Channel   Rev  Address         Exposed  Message
data-integrator            active      1  data-integrator   stable     13  10.152.183.142  no       
mysql             8.4.7    active      2  mysql             8.4/edge  109  10.152.183.68   no       
mysql-router      8.4.7    active      2  mysql-router      8.4/edge   68  10.152.183.52   no       

Unit                 Workload  Agent  Address     Ports  Message
data-integrator/0*   active    idle   10.1.12.3          
mysql/0*             active    idle   10.1.12.36         Primary
mysql/1              active    idle   10.1.12.34         
mysql-router/0*      active    idle   10.1.12.14         
mysql-router/1       active    idle   10.1.12.32  
```
