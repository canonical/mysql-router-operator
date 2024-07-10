1. remove `reconcile_partition` in machine_upgrade.py and upgrade.py
2. remove `if index ==1` block in authorized()
3. remove `if not self._upgrade.upgrade_resumed:` block in `_on_force_upgrade_action`
4. remove `if not self.upgrade_resumed:` block in `app_status` in upgrade.py
5. remove upgrade_resume property and property setter in machine_upgrade.py
6. remove upgrade_resume property in upgrade.py
7. in `_on_upgrade_charm`, remove `self._upgrade.upgrade_resumed = False`
8. in `on_upgrade_charm`, call reconcile for all units—not just leader
9. remove `_on_resume_upgrade_action` handler
