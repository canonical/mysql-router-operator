# Upgrade

**In-place upgrades/rollbacks are not possible for major versions.**

> Canonical is not planning to support in-place upgrades for major version changes. The new MySQL Router K8s charm will have to be installed nearby, and the data will be copied from the old to the new installation. After announcing the next MySQL major version support, the appropriate documentation for data migration will be published.

For instructions on carrying out **minor version upgrades**, see the following guides:

In-place minor upgrade:

* [Minor upgrade](/t/12345?channel=dpe/candidate), e.g. MySQL Router 8.0.33 -> MySQL Router 8.0.34<br/>
(including charm revision bump 99 -> 102).

* [Minor rollback](/t/12346?channel=dpe/candidate), e.g. MySQL Router 8.0.34 -> MySQL Router 8.0.33<br/>
(including charm revision return 102 -> 99).