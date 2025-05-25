## Juju version

The charm supports both [Juju 2.9 LTS](https://github.com/juju/juju/releases) and [Juju 3.1](https://github.com/juju/juju/releases).

The minimum supported Juju versions are:

* 2.9.32+
* 3.1.7+ (Juju secrets refactored/stabilized in Juju 3.1.7)

Make sure your machine meets the following requirements:
- Ubuntu 22.04 (Jammy) or later.
- 8GB of RAM.
- 2 CPU threads.
- At least 20GB of available storage.
- Access to the internet for downloading the required OCI/ROCKs and charms.

## Supported architectures

The charm is based on SNAP "[charmed-mysql](https://snapcraft.io/charmed-mysql)", which is currently available for `amd64` and `arm64` only! Please [contact us](/t/12323) if you are interested in new architecture!

<a name="mysql-gr-limits"></a>
## Charmed MySQL requirements
* Please also keep in mind ["Charmed MySQL" requirements](https://charmhub.io/mysql/docs/r-requirements).