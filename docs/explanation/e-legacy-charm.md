# Legacy charms
This page contains explanations regarding the legacy version of this charm. This includes clarification about Charmhub tracks, supported endpoints and interfaces, config options, and other important information.

## Summary
* [Charm types: "legacy" vs. "modern"](#heading--charm-types)
* [Default track `latest/` vs. track `1/`](#heading--default-track)
* [How to migrate to the modern charm](#heading--how-to-migrate)
* [How to deploy the legacy charm](#heading--how-to-deploy-legacy)
* [Features supported by the modern charm](#heading--features-supported-by-modern)
  * [Config options](#heading--config-options)
  * [Extensions](#heading--extensions)
  * [Roles](#heading--roles)
  * [MySQL versions](#heading--postgresql-versions)
  * [Architectures](#heading--architectures)
* [Contact us](#heading--contact-us)

--- 

<a href="#heading--charm-types"><h2 id="heading--charm-types"> Charm types: "legacy" vs. "modern" </h2></a>

There are [two types of charms](https://juju.is/docs/sdk/charm-taxonomy#heading--charm-types-by-generation) stored under the same charm name `mysql-router`:

1. [Reactive](https://juju.is/docs/sdk/charm-taxonomy#heading--reactive)  charm in the channel `latest/stable`, `8.0/stable`, `8.0.19/stable` (called `legacy`)
2. [Ops-based](https://juju.is/docs/sdk/ops) charm in the channel `dpe/candidate`, `8.4/edge` (called `modern`)

Both legacy and modern charms are [**subordinated**](https://juju.is/docs/sdk/charm-taxonomy#heading--subordinate-charms).

The legacy charm provided SQL endpoints `shared-db` (for the interface `mysql-shared`). The modern charm provides those old endpoint and a new endpoint `database` (for the interface `mysql_client`). Read more details about the available endpoints and interfaces [here](https://charmhub.io/mysql-router/docs/e-interfaces?channel=dpe/candidate).

**Note**: Please choose one endpoint to use. No need to relate all of them simultaneously!

<a href="#heading--default-track"><h2 id="heading--default-track"> Default track `latest/` vs. track `8.4/` </h2></a>

The [default track](https://docs.openstack.org/charm-guide/yoga/project/charm-delivery.html) will be switched from the `latest` to `8.4` soon. This is to ensure all new deployments use a modern codebase. We strongly advise against using the latest track, since a future charm upgrade may result in a MySQL Router version incompatible with an integrated application. Track `8.4/` guarantees a major router version 8.4 deployment only. The track `latest/` will be closed after all applications migrated from reactive to the ops-based charm.


<a href="#heading--how-to-migrate"><h2 id="heading--how-to-migrate"> How to migrate to the modern charm </h2></a>

The modern charm provides temporary support for the legacy interfaces:

**Quick try**: relate the current application with new charm using endpoint `shared-db` (set the channel to `dpe/candidate`). No extra changes necessary:

```
  mysql-router:
    charm: mysql-router
    channel: dpe/candidate
```

**Proper migration**: migrate the application to the new interface [`mysql_client`](https://github.com/canonical/charm-relation-interfaces). The application will connect MySQl Router using the [data_interfaces](https://charmhub.io/data-platform-libs/libraries/data_interfaces) library from [data-platform-libs](https://github.com/canonical/data-platform-libs/) via the endpoint `database`.

**Warning**: In-place upgrades are NOT possible! The reactive charm cannot be upgraded to the operator-framework-based one. The second/modern charm application must be launched nearby and relations should be switched from the legacy application to the modern one.


<a href="#heading--how-to-deploy-legacy"><h2 id="heading--how-to-deploy-legacy"> How to deploy the legacy charm </h2></a>

Deploy the charm using the channel `latest/stable`:

```
  mysql-router:
    charm: mysql-router
    channel: 8.0/stable
```

**Note**: remove Charm store prefix `cs:` from the bundle. Otherwise the modern charm will be chosen by Juju (due to the default track will be pointing to `8.4/stable` and not `latest/stable`). The common error message is: `cannot deploy application "mysql-router": unknown option "..."`.

<a href="#heading--features-supported-by-modern"><h2 id="heading--features-supported-by-modern"> Features supported by the modern charm </h2></a>
This section goes over the key differences in feature support and functionality between the legacy and modern charm.

<a href="#heading--config-options"><h3 id="heading--config-options"> Config options </h3></a>

The legacy charm config options were not moved to the modern charm, since the modern charm applies the best possible configuration automatically. Feel free to [contact us](/t/12323?channel=dpe/candidate) about the MySQl Router config options.

<a href="#heading--extensions"><h3 id="heading--extensions"> Extensions </h3></a>

Both legacy and modern charms provide no plugins/extensions support.

<a href="#heading--postgresql-versions"><h3 id="heading--postgresql-versions"> MySQL versions </h3></a>

At the moment, the modern MySQL Router charm supports relation to the modern Charmed MySQL 8.0 (based on Jammy/22.04 series) only.
Please [contact us](/t/12323?channel=dpe/candidate) if you need different versions/series.

<a href="#heading--architectures"><h3 id="heading--architectures"> Architectures </h3></a>

Currently, the modern charm supports architecture `amd64` and `arm64` only.

<a href="#heading--contact-us"><h2 id="heading--contact-us"> Report issues </h2></a>

The "legacy charm" (from `latest/stable`) is stored on [Launchpad](TODO). Report legacy charm issues [here](TODO).

The "modern charm" (from `dpe/candidate`) is stored on [GitHub](https://github.com/canonical/mysql-router-operator). Report modern charm issues [here](https://github.com/canonical/mysql-router-operator/issues/new/choose).

Do you have questions? [Reach out](/t/12323?channel=dpe/candidate) to us!