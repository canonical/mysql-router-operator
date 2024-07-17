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

# Contents

1. [Tutorial](tutorial)
  1. [1. Introduction](tutorial/t-overview.md)
  1. [2. Set up the environment](tutorial/t-setup-environment.md)
  1. [3. Deploy MySQL Router](tutorial/t-deploy-charm.md)
  1. [4. Manage units](tutorial/t-managing-units.md)
  1. [5. Enable security](tutorial/t-enable-security.md)
  1. [6. Cleanup environment](tutorial/t-cleanup-environment.md)
1. [How To](how-to)
  1. [Setup](how-to/h-setup)
    1. [Deploy on LXD](how-to/h-setup/h-deploy-lxd.md)
    1. [Manage units](how-to/h-setup/h-manage-units.md)
    1. [Enable encryption](how-to/h-setup/h-enable-encryption.md)
    1. [Manage applications](how-to/h-setup/h-manage-app.md)
  1. [Monitoring](how-to/h-monitoring)
    1. [Monitoring (COS)](how-to/h-monitoring/h-enable-monitoring.md)
    1. [Tracing (COS)](how-to/h-monitoring/h-enable-tracing.md)
  1. [Upgrade](how-to/h-upgrade)
    1. [Intro](how-to/h-upgrade/h-upgrade-intro.md)
    1. [Major upgrade](how-to/h-upgrade/h-upgrade-major.md)
    1. [Major rollback](how-to/h-upgrade/h-rollback-major.md)
    1. [Minor upgrade](how-to/h-upgrade/h-upgrade-minor.md)
    1. [Minor rollback](how-to/h-upgrade/h-rollback-minor.md)
  1. [Contribute](how-to/h-contribute.md)
1. [Reference](reference)
  1. [Release Notes](reference/r-releases-group)
    1. [All releases](reference/r-releases-group/r-releases.md)
    1. [Revision 197/198](reference/r-releases-group/r-releases-rev197.md)
    1. [Revision 118/119](reference/r-releases-group/r-releases-rev119.md)
  1. [Requirements](reference/r-requirements.md)
  1. [Testing](reference/r-testing.md)
  1. [Contacts](reference/r-contacts.md)
1. [Explanation](explanation)
  1. [Interfaces/endpoints](explanation/e-interfaces.md)
  1. [Statuses](explanation/e-statuses.md)
  1. [Juju](explanation/e-juju-details.md)