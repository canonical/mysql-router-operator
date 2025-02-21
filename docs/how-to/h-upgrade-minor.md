# Minor Upgrade

> :information_source: **Example**: MySQL Router 8.0.33 -> MySQL Router 8.0.34<br/>
(including simple charm revision bump: from revision 99 to revision 102)

We strongly recommend to **NOT** perform any other extraordinary operations on Charmed MySQL cluster and/or MySQL Router, while upgrading. As an examples, these may be (but not limited to) the following:

1. Adding or removing units
2. Creating or destroying new relations
3. Changes in workload configuration
4. Upgrading other connected/related/integrated applications simultaneously

The concurrency with other operations is not supported, and it can lead the cluster into inconsistent states.

> **:warning: NOTE:** Make sure to have a [Charmed MySQL backups](/t/9896) of your data when running any type of upgrades.

> **:warning: TIP:** The "MySQL Router" upgrade should follow first, before "Charmed MySQL" upgrade!!!

## Minor upgrade steps

TODO