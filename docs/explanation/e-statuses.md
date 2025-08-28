# Charm Statuses

> :warning: **WARNING** : it is an work-in-progress article. Do NOT use it in production! Contact [Canonical Data Platform team](https://chat.charmhub.io/charmhub/channels/data-platform) if you are interested in the topic.

The charm follows [standard Juju applications statuses](https://juju.is/docs/olm/status-values#heading--application-status). Here you can find the expected end-users reaction on different statuses:

| Juju Status | Message | Expectations | Actions |
|-------|-------|-------|-------|
| **active** | any | Normal charm operations | No actions required |
| **waiting** | any | Charm is waiting for relations to be finished | No actions required |
| **maintenance** | any | Charm is performing the internal maintenance (e.g. re-configuration) | No actions required |
| **blocked** | any | The manual user activity is required! | Follow the message hints (see below) |
| **blocked** | Missing relation: ...  | Normal behavior, charm needs all relations to work. | Follow the hint to establish a proper relation. |
| **blocked** | Router was manually removed from MySQL ClusterSet. Remove & re-deploy unit | Scale-down temporary message OR split-brain for the unknown reason. | Wait to finish scale-down or remove and re-deploy unit if the message is persistent.|
| **blocked** | ... app requested unsupported extra user role on database endpoint | Unsupported [role](https://charmhub.io/data-integrator/configure#extra-user-roles) requested. | Use supported extra-user-role. |
| **blocked** | Upgrade incompatible. Rollback to previous revision with `juju refresh` | Incompatible charm channel/revision chosen. | [Rollback](/t/12239) the charm. |
| **blocked** | Upgrading. Verify highest unit is healthy & run `resume-upgrade ` action. To rollback, `juju refresh` to last revision | Normal behavior, application is being upgraded and waiting for user confirmation to continue or rollback | [Continue upgrade](/t/12238) or [rollback](/t/12239). |
| **error** | any | An unhanded internal error happened | Read the message hint. Execute `juju resolve <error_unit/0>` after addressing the root of the error state |
| **terminated** | any | The unit is gone and will be cleaned by Juju soon | No actions possible |
| **unknown** | any | Juju doesn't know the charm app/unit status. Possible reason: the charm termination in progress. | Manual investigation required if status is permanent |