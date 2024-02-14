## Juju version

The charm supports both [Juju 2.9 LTS](https://github.com/juju/juju/releases) and [Juju 3.1](https://github.com/juju/juju/releases).

The minimum supported Juju versions are:

* 2.9.32+
* 3.1.6+ (due to issues with Juju secrets in previous versions, see [#1](https://bugs.launchpad.net/juju/+bug/2029285) and [#2](https://bugs.launchpad.net/juju/+bug/2029282))

## Minimum requirements

Make sure your machine meets the following requirements:
- Ubuntu 20.04 (Focal) or later.
- 8GB of RAM.
- 2 CPU threads.
- At least 20GB of available storage.
- Access to the internet for downloading the required OCI/ROCKs and charms.

## Supported architectures

The charm is based on SNAP "[charmed-mysql](https://snapcraft.io/charmed-mysql)", which is currently available for `amd64` only! The architecture `arm64` support is planned. Please [contact us](/t/12323) if you are interested in new architecture!

<a name="mysql-gr-limits"></a>
## Charmed MySQL requirements
* Please also keep in mind ["Charmed MySQL" requirements](https://charmhub.io/mysql/docs/r-requirements).