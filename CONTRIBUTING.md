# Contributing

## Overview

This documents explains the processes and practices recommended for contributing enhancements to
this operator.

- Generally, before developing enhancements to this charm, you should consider
  [opening an issue
  ](https://github.com/canonical/mysql-router-operator/issues) explaining
  your use case.
- If you would like to chat with us about your use-cases or proposed
  implementation, you can reach us at [Canonical Mattermost public
  channel](https://chat.charmhub.io/charmhub/channels/charm-dev) or
  [Discourse](https://discourse.charmhub.io/).
- Familiarising yourself with the [Charmed Operator
  Framework](https://juju.is/docs/sdk) library will help you a lot when working
  on new features or bug fixes.
- All enhancements require review before being merged. Code review typically
  examines
  - code quality
  - test coverage
  - user experience for Juju administrators this charm.
- Please help us out in ensuring easy to review branches by rebasing your pull
  request branch onto the `main` branch. This also avoids merge commits and
  creates a linear Git commit history.

## Developing

### Environment set up

This operator charm can be deployed locally using [Juju on a localhost LXD
cloud](https://juju.is/docs/olm/lxd). If you do not already have a Juju
controller bootstrapped, you can set one up by doing the following:

```
# install requirements
sudo snap install charmcraft --classic
sudo snap install lxd
sudo snap install juju --classic

# configure lxd
sudo adduser $USER lxd
newgrp lxd
lxd init --auto
lxc network set lxdbr0 ipv6.address none

# bootstrap controller to lxd
juju clouds
juju bootstrap localhost overlord
```

Clone this repository:
```shell
git clone https://github.com/canonical/mysql-router-operator.git
cd mysql-router-operator
```

Install `tox`, `poetry`, and `charmcraftcache`

Install pipx: https://pipx.pypa.io/stable/installation/
```shell
pipx install tox
pipx install poetry
pipx install charmcraftcache
```

You can create an environment for development:

```shell
poetry install
```

### Testing

```shell
tox run -e format        # update your code according to linting rules
tox run -e lint          # code style
tox run -e unit          # unit tests
charmcraft test lxd-vm:  # integration tests
tox                      # runs 'lint' and 'unit' environments
```

## Build charm

Build the charm in this git repository using:

```shell
charmcraftcache pack
```

### Deploy

```bash
# Create a model
juju add-model dev
# Enable DEBUG logging
juju model-config logging-config="<root>=INFO;unit=DEBUG"
# Deploy the charm
juju deploy ./mysqlrouter-operator_ubuntu-20.04-amd64.charm
```

## Canonical Contributor Agreement

Canonical welcomes contributions to the Charmed MySQL-Router Operator. Please
check out our [contributor agreement](https://ubuntu.com/legal/contributors) if
you're interested in contributing to the solution.
