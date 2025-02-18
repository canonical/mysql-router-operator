>Reference > Release Notes > [All revisions](/t/12318) > Revision 118/119
# Revision 118/119 (`dpe/beta` only)
<sub>October 6, 2023</sub>

Dear community, this is to inform you that new MySQL Router is published in `dpe/candidate` [charmhub](https://charmhub.io/mysql-router?channel=dpe/beta) channel for VMs:

|   |AMD64|
|---:|:---:|
| Revisions: | 119 (`jammy`) / 118 (`focal`) | 

## The features you can start using today:

* [Add Juju 3 support](/t/12179) (Juju 2 is still supported)
* Charm [minor upgrades](/t/12345) and [minor rollbacks](/t/12346)
* Workload updated to [MySQL Router 8.0.34](https://dev.mysql.com/doc/relnotes/mysql/8.0/en/news-8-0-34.html)
* [Support](https://charmhub.io/mysql-router/integrations?channel=dpe/stable) for modern `mysql_client` and `tls-certificates` interfaces
* Support `juju expose`
* New and complete documentation on CharmHub

## Bugfixes included:

Canonical Data issues are now public on both [Jira](https://warthogs.atlassian.net/jira/software/c/projects/DPE/issues/) and [GitHub](https://github.com/canonical/mysql-router-operator/issues) platforms.<br/>[GitHub Releases](https://github.com/canonical/mysql-router-operator/releases) provide a detailed list of bugfixes/PRs/Git commits for each revision.

## What is inside the charms:

* MySQL Router charm ships the latest MySQL Router “8.0.34-0ubuntu0.22.04.1”
* CLI mysql-shell updated to "8.0.34-0ubuntu0.22.04.1~ppa1"
* The Prometheus mysql-router-exporter is "4.0.5-0ubuntu0.22.04.1~ppa1"
* VM charms based on [Charmed MySQL](https://snapcraft.io/charmed-mysql) SNAP (Ubuntu LTS “22.04” - ubuntu:22.04-based)
* Principal charms supports the latest LTS series “22.04” only.
* Subordinate charms support LTS “22.04” and “20.04” only.

## Technical notes:

* Upgrade (`juju refresh`) is possible from this revision 69+.
* Use this operator together with a modern operator "[Charmed MySQL](https://charmhub.io/mysql)".

## How to reach us:

If you would like to chat with us about your use-cases or ideas, you can reach us at [Canonical Mattermost public channel](https://chat.charmhub.io/charmhub/channels/data-platform) or [Discourse](https://discourse.charmhub.io/). Check all other contact details [here](/t/12177).

Consider [opening a GitHub issue](https://github.com/canonical/mysql-router-operator/issues) if you want to open a bug report.<br/>[Contribute](https://github.com/canonical/mysql-router-operator/blob/main/CONTRIBUTING.md) to the project!

## Footer:

It is the first stable release of the operator "MySQL Router" by Canonical Data.<br/>Well done, Team!