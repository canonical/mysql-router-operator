> Reference > Release Notes > [All releases] > Revision 223/224/225

# Revision 223/224/225 (`dpe/candidate` only)
<sub>December 2, 2024</sub>

Dear community,

Canonical's newest Charmed MySQL Router operator has been published in the [`dpe/candidate` channel].

Due to the newly added support for `arm64` architecture and Ubuntu `20.04 LTS` base, the MySQL Router charm now releases three revisions simultaneously:
* Revision 223 is built for `amd64` on `20.04 LTS`
* Revision 224 is built for `amd64` on `22.04 LTS`
* Revision 225 is built for `arm64` on `22.04 LTS`

To make sure you deploy for the right architecture, we recommend setting an [architecture constraint](https://juju.is/docs/juju/constraint#heading--arch) for your entire Juju model.

Otherwise, you can specify the architecture at deploy time with the `--constraints` flag as follows:

```shell
juju deploy mysql-router --constraints arch=<arch>
```
where `<arch>` can be `amd64` or `arm64`.

Since MySQL Router is a subordinate charm, it will automatically use the same base as the principal charm.

---

## Highlights

Below is an overview of the major highlights, enhancements, and bugfixes in this revision. For a detailed list of all commits since the last stable release, see the [GitHub release notes].

### Enhancements
* Upgraded MySQL from `v8.0.36` -> `v8.0.37` (see [Packaging](#packaging))
* Added support or ARM64 architecture ([PR #472](https://github.com/canonical/mysql-operator/pull/472)) 

### Bugfixes
* Stabilized exporter tests by using listen-port to avoid ephemeral ports in [PR #154](https://github.com/canonical/mysql-router-operator/pull/154) ([DPE-4173](https://warthogs.atlassian.net/browse/DPE-4173))
* Fixed release CI in [PR #152](https://github.com/canonical/mysql-router-operator/pull/152)
* Updated Python dependencies

## Technical details
This section contains some technical details about the charm's contents and dependencies. 

If you are jumping over several stable revisions, check [previous release notes][All releases] before upgrading.

### Requirements
See the [system requirements] page in the MySQL documentation for more details about software and hardware prerequisites.

### Packaging
This charm is based on the [`charmed-mysql` snap] Revision [113/114][snap rev113/114]. It packages:
- mysql-router `v8.0.37`
  - [8.0.37-0ubuntu0.22.04.1]
- mysql-shell `v8.0.37`
  - [8.0.37+dfsg-0ubuntu0.22.04.1~ppa3]
- prometheus-mysqld-exporter `v0.14.0`
  - [0.14.0-0ubuntu0.22.04.1~ppa2]

### Libraries and interfaces
* **mysql `v0`**
  * See the API reference in the [MySQL Libraries tab]
* **grafana_agent `v0`** for integration with Grafana 
    * Implements  `cos_agent` interface
* **rolling_ops `v0`** for rolling operations across units 
    * Implements `rolling_op` interface
* **tempo_k8s `v1`, `v2`** for integration with Tempo charm
    * Implements `tracing` interface
* **tls_certificates_interface `v2`** for integration with TLS charms
    * Implements `tls-certificates` interface

See the [`/lib/charms` directory on GitHub] for a full list of supported libraries.

See the [Integrations tab] for a full list of supported integrations/interfaces/endpoints.

## Contact us
  
Charmed MySQL is an open source project that warmly welcomes community contributions, suggestions, fixes, and constructive feedback.  
* Raise software issues or feature requests on [**GitHub**](https://github.com/canonical/mysql-operator/issues)  
*  Report security issues through [**Launchpad**](https://wiki.ubuntu.com/DebuggingSecurity#How%20to%20File)  
* Contact the Canonical Data Platform team through our [Matrix](https://matrix.to/#/#charmhub-data-platform:ubuntu.com) channel.

<!-- LINKS -->
[`dpe/candidate` channel]: https://charmhub.io/mysql-router?channel=dpe/candidate
[GitHub release notes]: https://github.com/canonical/mysql-router-operator/releases/tag/rev225

[All releases]: /t/12318
[system requirements]: https://charmhub.io/mysql/docs/r-system-requirements
[How to upgrade Juju for a new database revision]: /t/14325

[Integrations tab]: https://charmhub.io/mysql-router/integrations?channel=dpe/candidate
[MySQL Libraries tab]: https://charmhub.io/mysql/libraries

[`/lib/charms` directory on GitHub]: https://github.com/canonical/mysql-router-operator/tree/main/lib/charms

[snap rev113/114]: https://github.com/canonical/charmed-mysql-snap/releases/tag/rev114
[`charmed-mysql` snap]: https://snapcraft.io/charmed-mysql

[8.0.37-0ubuntu0.22.04.1]: https://launchpad.net/ubuntu/+source/mysql-8.0/8.0.37-0ubuntu0.22.04.3
[8.0.37+dfsg-0ubuntu0.22.04.1~ppa3]: https://launchpad.net/~data-platform/+archive/ubuntu/mysql-shell
[0.14.0-0ubuntu0.22.04.1~ppa2]: https://launchpad.net/~data-platform/+archive/ubuntu/mysqld-exporter