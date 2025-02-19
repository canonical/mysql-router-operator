>Reference > Release Notes > [All revisions] > Revision 267/268/269

# Revision 267/268/269 (`dpe/candidate` only)

Dear community,

Canonical's newest Charmed MySQL Router operator has been published in the `dpe/candidate` channel.

Due to the newly added support for `arm64` architecture, the MySQL Router charm now releases multiple revisions simultaneously:
* Revision 267 is built for `amd64` on Ubuntu 22.04 LTS
* Revision 268 is built for `amd64` on Ubuntu 20.04 LTS
* Revision 269 is built for `arm64` on Ubuntu 22.04 LTS

To make sure you deploy for the right architecture, we recommend setting an [architecture constraint](https://juju.is/docs/juju/constraint#heading--arch) for your entire juju model.

Otherwise, it can be done at deploy time with the `--constraints` flag:
```shell
juju deploy mysql-router --constraints arch=<arch> 
```
where `<arch>` can be `amd64` or `arm64`.

---

## Highlights 

* Updated MySQL Router to [v8.0.39](https://dev.mysql.com/doc/relnotes/mysql/8.0/en/news-8-0-39.html) ([PR #172](https://github.com/canonical/mysql-router-operator/pull/172)) ([DPE-4573](https://warthogs.atlassian.net/browse/DPE-4573))
* Added support for [hacluster](https://charmhub.io/hacluster) ([PR #177](https://github.com/canonical/mysql-router-operator/pull/177)) ([DPE-5249](https://warthogs.atlassian.net/browse/DPE-5249))
* [Add Tracing support](/t/14785) ([PR #180](https://github.com/canonical/mysql-router-operator/pull/180)) ([DPE-5312](https://warthogs.atlassian.net/browse/DPE-5312))
* Added warnings to destructive actions ([PR #188](https://github.com/canonical/mysql-router-operator/pull/188)) ([DPE-5711](https://warthogs.atlassian.net/browse/DPE-5711))
* Use ruff as a linter and formatter ([PR #162](https://github.com/canonical/mysql-router-operator/pull/162)) ([DPE-3881](https://warthogs.atlassian.net/browse/DPE-3881))

## Bugfixes

This release contains no new bugfixes but library/dependencies updates only:
[details=Libraries, testing, and CI]
* Run tests on juju 3.6 on a nightly schedule ([PR #173](https://github.com/canonical/mysql-router-operator/pull/173)) ([DPE-4976](https://warthogs.atlassian.net/browse/DPE-4976))
* Update 3.6 nightly tests to run against 3.6/candidate instead of 3.6/beta ([PR #187](https://github.com/canonical/mysql-router-operator/pull/187))
* Run juju 3.6 nightly tests against 3.6/stable ([PR #189](https://github.com/canonical/mysql-router-operator/pull/189))
* Switch from tox build wrapper to charmcraft.yaml overrides ([PR #178](https://github.com/canonical/mysql-router-operator/pull/178))
* Update canonical/charming-actions action to v2.6.3 ([PR #155](https://github.com/canonical/mysql-router-operator/pull/155))
* Update codecov/codecov-action action to v5 ([PR #186](https://github.com/canonical/mysql-router-operator/pull/186))
* Update data-platform-workflows to v21 ([PR #168](https://github.com/canonical/mysql-router-operator/pull/168))
* Update data-platform-workflows to v21.0.1 ([PR #174](https://github.com/canonical/mysql-router-operator/pull/174))
* Update data-platform-workflows to v23 ([PR #181](https://github.com/canonical/mysql-router-operator/pull/181))
* Update dependency cryptography to v43 [SECURITY] ([PR #176](https://github.com/canonical/mysql-router-operator/pull/176))
[/details]


### Requirements and compatibility

If you are jumping over several stable revisions, check [previous release notes][All revisions] before upgrading.

See the [system requirements] for more details about Juju versions and other software and hardware prerequisites.

See the [`/lib/charms` directory on GitHub] for details about **charm libraries**.

See the [`metadata.yaml` file on GitHub] for a full list of **supported interfaces**.

### Packaging

This charm is based on the Charmed MySQL snap revision 121/122.

<!-- Topics -->
[All revisions]: /t/12318
[system requirements]: /t/12325

<!-- GitHub -->
[`/lib/charms` directory on GitHub]: https://github.com/canonical/mysql-router-operator/tree/main/lib/charms
[`metadata.yaml` file on GitHub]: https://github.com/canonical/mysql-router-operator/blob/main/metadata.yaml

<!-- Charmhub -->
[dpe/candidate channel]: https://charmhub.io/mysql-router?channel=dpe/candidate

<!-- Snap/Rock -->
[`charmed-mysql-router` packaging]: https://github.com/canonical/charmed-mysql-router-snap

[MySQL Libraries tab]: https://charmhub.io/mysql/libraries

[rock image]: https://github.com/canonical/charmed-mysql-rock/pkgs/container/charmed-mysql

[mysql-router `v8.0.37`]: https://launchpad.net/ubuntu/+source/mysql-8.0/8.0.37-0ubuntu0.24.04.1
[mysql-shell `v8.0.37`]: https://launchpad.net/~data-platform/+archive/ubuntu/mysql-shell
[prometheus-mysqlrouter-exporter `v5.0.1`]: https://launchpad.net/~data-platform/+archive/ubuntu/mysqlrouter-exporter