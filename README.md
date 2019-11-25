# Phabricator-maintenance-bot
Source for https://phabricator.wikimedia.org/p/Maintenance_bot/

* `column_mover.py` is a script that can perform additional actions when someone drags/changes a task in a workboard to a different column. E.g. Moving a task in workborad #user-ladsgroup from column "incoming" to column "done" will automatically change the task's status to "done"
* `patchforreview_remover.py` is an automatic script that removes the "patch_for_review" tag when all patches have been merged or abandoned
