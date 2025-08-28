# Deploy MySQL Router

Please follow the [Tutorial](/t/12334) to deploy the charm on LXD.

Short story for your Ubuntu 22.04 LTS:
```shell
sudo snap install multipass
multipass launch --cpus 4 --memory 8G --disk 30G --name my-vm charm-dev # tune CPU/RAM/HDD accordingly to your needs
multipass shell my-vm

juju add-model mysql
juju deploy mysql --channel 8.0/stable
juju deploy mysql-router --channel dpe/edge
juju deploy mysql-test-app
juju integrate mysql mysql-router
juju integrate mysql-router mysql-test-app:database

juju status --watch 1s
```

The expected result:
```shell
Model  Controller  Cloud/Region         Version  SLA          Timestamp
mysql  lxd         localhost/localhost  3.1.6    unsupported  11:57:33+02:00

App             Version          Status  Scale  Charm           Channel     Rev  Exposed  Message
mysql           8.0.34-0ubun...  active      1  mysql           8.0/stable  196  no       
mysql-router    8.0.34-0ubun...  active      1  mysql-router    dpe/edge    119  no       
mysql-test-app  0.0.2            active      1  mysql-test-app  stable       26  no       

Unit               Workload  Agent  Machine  Public address  Ports           Message
mysql-test-app/0*  active    idle   1        10.3.217.209                    
  mysql-router/0*  active    idle            10.3.217.209                    
mysql/0*           active    idle   0        10.3.217.119    3306,33060/tcp  Primary

Machine  State    Address       Inst id        Base          AZ  Message
0        started  10.3.217.119  juju-d458a0-0  ubuntu@22.04      Running
1        started  10.3.217.209  juju-d458a0-1  ubuntu@22.04      Running
```

Check the [Testing](/t/12324) reference to test your deployment.