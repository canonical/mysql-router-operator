# MySQL Router Documentation

The MySQL Router Operator delivers automated operations management from [day 0 to day 2](https://codilime.com/blog/day-0-day-1-day-2-the-software-lifecycle-in-the-cloud-age/) on the [MySQL Router Community Edition](https://www.mysql.com/products/community/) lightweight middleware that provides transparent routing between your application and back-end MySQL Servers. It is an open source, end-to-end, production-ready data platform component [on top of Juju](https://juju.is/).

![image|690x424](upload://vpevillwv3S9C44LDFBxkGCxpGq.png)

MySQL Router is part of InnoDB Cluster, and is lightweight middleware that provides transparent routing between your application and back-end MySQL Servers. It can be used for a wide variety of use cases, such as providing high availability and scalability by effectively routing database traffic to appropriate back-end MySQL Servers. The pluggable architecture also enables developers to extend MySQL Router for custom use cases.

This MySQL Router operator charm comes in two flavours to deploy and operate MySQL Router on [physical/virtual machines](https://github.com/canonical/mysql-router-operator) and [Kubernetes](https://github.com/canonical/mysql-router-k8s-operator). Both offer features identical set of features and simplifies deployment, scaling, configuration and management of MySQL Router in production at scale in a reliable way.

## Project and community

This MySQL Router charm is an official distribution of MySQL Router. It’s an open-source project that welcomes community contributions, suggestions, fixes and constructive feedback.
- [Read our Code of Conduct](https://ubuntu.com/community/code-of-conduct)
- [Join the Discourse forum](https://discourse.charmhub.io/tag/mysql-router)
- [Contribute](https://github.com/canonical/mysql-router-operator/blob/main/CONTRIBUTING.md) and report [issues](https://github.com/canonical/mysql-router-operator/issues/new/choose)
- Explore [Canonical Data Fabric solutions](https://canonical.com/data)
-  [Contacts us]() for all further questions

## In this documentation

| | |
|--|--|
|  [Tutorials]()</br>  Get started - a hands-on introduction to using Charmed MySQL operator for new users </br> |  [How-to guides]() </br> Step-by-step guides covering key operations and common tasks |
| [Reference](https://charmhub.io/mysql-router/actions) </br> Technical information - specifications, APIs, architecture | [Explanation]() </br> Concepts - discussion and clarification of key topics  |

# Navigation

[details=Navigation]

| Level | Path | Navlink |
|---------|---------|-------------|
| 1 | tutorial | [Tutorial]() |
| 2 | t-overview | [1. Introduction](/t/12332) |
| 2 | t-setup-environment | [2. Set up the environment](/t/12333) |
| 2 | t-deploy-charm | [3. Deploy MySQL Router](/t/12334) |
| 2 | t-managing-units | [4. Manage units](/t/12335) |
| 2 | t-enable-security | [5. Enable security](/t/12336) |
| 2 | t-cleanup-environment | [6. Cleanup environment](/t/12337) |
| 1 | how-to | [How To]() |
| 2 | h-setup | [Setup]() |
| 3 | h-deploy-lxd | [Deploy on LXD](/t/12340) |
| 3 | h-manage-units | [Manage units](/t/12338) |
| 3 | h-enable-encryption | [Enable encryption](/t/12341) |
| 3 | h-manage-app | [Manage applications](/t/12339) |
| 3 | h-external-access | [External access](/t/15696) | 
| 2 | h-monitoring | [Monitoring]() |
| 3 | h-enable-monitoring | [Monitoring (COS)](/t/14094) |
| 3 | h-enable-tracing | [Tracing (COS)](/t/14785) |
| 2 | h-upgrade | [Upgrade](/t/12342) |
| 3 | h-upgrade-minor | [Minor upgrade](/t/12345) |
| 3 | h-rollback-minor | [Minor rollback](/t/12346) |
| 2 | h-contribute | [Contribute](/t/14656) |
| 1 | reference | [Reference]() |
| 2 | r-releases | [Releases](/t/12318) |
| 2 | r-system-requirements | [System requirements](/t/12325) |
| 2 | r-testing | [Testing](/t/12324) |
| 2 | r-contacts | [Contacts](/t/12323) |
| 1 | explanation | [Explanation]() |
| 2 | e-interfaces | [Interfaces/endpoints](/t/12322) |
| 2 | e-statuses | [Statuses](/t/12321) |
| 2 | e-juju-details | [Juju](/t/12320) |
| 2 | e-legacy-charm | [Legacy charm](/t/15370) |

[/details]

<!--Archived
| 3 | h-upgrade-major | [Major upgrade](/t/12343) |
| 3 | h-rollback-major | [Major rollback](/t/12344) |

| 3 | r-releases-rev269 | [Revision 267/268/269](/t/16074)
| 3 | r-releases-rev225 | [Revision 223/224/225](/t/15360)
| 3 | r-releases-rev198 | [Revision 197/198](/t/14073) |
| 3 | r-releases-rev119 | [Revision 118/119](/t/12319) |
-->