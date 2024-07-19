>Reference > Release Notes > [All revisions](/t/12318) > Revision 185/186
# Revision 185/186 (`dpe/candidate` only)

<sub>TODO: DD, MM, YYYY</sub>

Dear community,

We'd like to announce that Canonical's newest Charmed MySQL Router operator has been published in the 'dpe/stable' [channel](/t/12318?channel=dpe/candidate) :tada: :

|   |AMD64|
|---:|:---:|
| Revisions: | 186 (`jammy`) / 185 (`focal`) | 

[note]
If you are jumping over several stable revisions, make sure to check [previous release notes](/t/12318?channel=dpe/candidate) before upgrading to this revision.
[/note]  

## Features you can start using today

* New workload version [MySQL Router 8.0.36](https://dev.mysql.com/doc/relnotes/mysql/8.0/en/news-8-0-36.html) [[PR#113](https://github.com/canonical/mysql-router-operator/pull/113)][[DPE-3717](https://warthogs.atlassian.net/browse/DPE-3717)]
* Exposure of all endpoints via data-integrator + TLS support [[PR#119](https://github.com/canonical/mysql-router-operator/pull/119)][[DPE-3689](https://warthogs.atlassian.net/browse/DPE-3689), [DPE-4179](https://warthogs.atlassian.net/browse/DPE-4179)]
* Support for subordination with `ubuntu-advantage` and `landscape-client` [[PR#115](https://github.com/canonical/mysql-router-operator/pull/115)]
* In-place upgrades [[PR#88](https://github.com/canonical/mysql-router-operator/pull/88)] + Router version in upgrade status [[#128](https://github.com/canonical/mysql-router-operator/pull/128)]
* [Observability with COS](/t/14094) [[#93](https://github.com/canonical/mysql-router-operator/pull/93)][[DPE-1794](https://warthogs.atlassian.net/browse/DPE-1794)]
* Log rotation via cron in [[PR#80](https://github.com/canonical/mysql-router-operator/pull/80)][[DPE-1789](https://warthogs.atlassian.net/browse/DPE-1789)]
* Discourse documentation [[PR#81](https://github.com/canonical/mysql-router-operator/pull/81)][[DPE-2752](https://warthogs.atlassian.net/browse/DPE-2752)]
* All the functionality from [previous revisions](/t/12318)  

## Bugfixes

* Added integration test for upgrades in [PR#135](https://github.com/canonical/mysql-router-operator/pull/135), [[DPE-4179](https://warthogs.atlassian.net/browse/DPE-4179), [DPE-4219](https://warthogs.atlassian.net/browse/DPE-4219)]
* Updated `charmed-mysql-snap` to the latest edge revision in [PR#144](https://github.com/canonical/mysql-router-operator/pull/144)
* Check if highest unit has upgraded before resuming upgrade in [PR#140](https://github.com/canonical/mysql-router-operator/pull/140)
* No longer returning upgrade app status if upgrade not in progress in [PR#141](https://github.com/canonical/mysql-router-operator/pull/141)
* Removed redundant upgrade check  in [PR#137](https://github.com/canonical/mysql-router-operator/pull/137)
* Fixed missing kwargs in some methods in [PR#143](https://github.com/canonical/mysql-router-operator/pull/143), [[DPE-4219](https://warthogs.atlassian.net/browse/DPE-4219)]
* Updated `force-upgrade` action description in [PR#133](https://github.com/canonical/mysql-router-operator/pull/133)
* Recovery from hook errors when creating/deleting MySQL users in [PR#112](https://github.com/canonical/mysql-router-operator/pull/112)
* Fixed retry if MySQL Server is unreachable in [PR#104](https://github.com/canonical/mysql-router-operator/pull/104)
* Bootstrap with force by default in [PR#100](https://github.com/canonical/mysql-router-operator/pull/100)
* Updated the logrotation dateformat to tolerate more than 24hrs of uptime in [PR#94](https://github.com/canonical/mysql-router-operator/pull/94), [[DPE-3063](https://warthogs.atlassian.net/browse/DPE-3063)] 
* Made `install` handler idempotent in [PR#92](https://github.com/canonical/mysql-router-operator/pull/92)

Canonical Data issues are now public on both [Jira](https://warthogs.atlassian.net/jira/software/c/projects/DPE/issues/) and [GitHub](https://github.com/canonical/mysql-router-operator/issues) platforms.  
[GitHub Releases](https://github.com/canonical/mysql-router-operator/releases) provide a detailed list of bugfixes, PRs, and commits for each revision.  

## Inside the charms

* MySQL Router charm ships the latest MySQL Router `8.0.36-0ubuntu0.22.04.1`
* CLI mysql-shell updated to `8.0.36+dfsg-0ubuntu0.22.04.1~ppa4`
* The Prometheus mysql-router-exporter is `5.0.1-0ubuntu0.22.04.1~ppa1`
* VM charms based on [Charmed MySQL SNAP](https://github.com/canonical/charmed-mysql-snap) (Ubuntu LTS `22.04.4`) revision `103`.
* Subordinate charms support LTS 22.04 and 20.04 only.

## Technical notes

* Upgrade (`juju refresh`) is possible from revision 118/119+
* Use this operator together with modern operator [Charmed MySQL](https://charmhub.io/mysql)
* Please check restrictions from [previous release notes](https://charmhub.io/mysql-router/docs/r-releases?channel=dpe/edge) 

## Contact us

Charmed MySQL Router is an open source project that warmly welcomes community contributions, suggestions, fixes, and constructive feedback.  
* Raise software issues or feature requests on [**GitHub**](https://github.com/canonical/mysql-router-operator/issues)  
*  Report security issues through [**Launchpad**](https://wiki.ubuntu.com/DebuggingSecurity#How%20to%20File)  
* Contact the Canonical Data Platform team through our [Matrix](https://matrix.to/#/#charmhub-data-platform:ubuntu.com) channel.