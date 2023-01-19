import re
import time
from collections import defaultdict

from lib import Client


class Checker():
    def __init__(self, gerrit_bot_phid, project_patch_for_review_phid, client):
        self.gerrit_bot_phid = gerrit_bot_phid
        self.project_patch_for_review_phid = project_patch_for_review_phid
        self.client = client

    def check(self, t_id):
        """
        Returns true if the Patch-For-Review project should be removed from the Phabricator
        task identified 't_id'.
        """
        phid = self.client.lookupPhid(t_id)
        return self.phid_check(phid)

    def phid_check(self, phid) -> bool:
        """
        Returns true if the Patch-For-Review project should be removed from the Phabricator
        task identified by 'phid'.
        """
        gerrit_bot_actions = []

        # Note that transactions are returned in reverse chronological order (most recent first).
        for transaction in self.client.getTransactions(phid):
            if re.findall(re.escape('https://github.com/') + r'.+?/pull', str(transaction)):
                return False
            if transaction['authorPHID'] == self.gerrit_bot_phid:
                gerrit_bot_actions.append(transaction)
            else:
                # If someone other than GerritBot adds the Patch-For-Review project, don't
                # auto-remove it.
                if transaction['type'] == 'projects':
                    check = self.project_patch_for_review_phid in str(
                        transaction['fields'])
                    add_check = "'add'" in str(transaction['fields'])
                    if check and add_check:
                        return False

        gerrit_patch_status = defaultdict(list)
        for case in gerrit_bot_actions:
            if case['type'] != 'comment':
                continue

            if len(case['comments']) != 1:
                return False
            raw_comment = case['comments'][0]['content']['raw']
            gerrit_patch_id = re.findall(
                r'https://gerrit(?:-test|)\.wikimedia\.org/r/(\d+)(?:$|\]\])', raw_comment)[0]
            merged = re.findall(
                r'Change \d+ \*\*(?:merged|abandoned)\*\* by ',
                raw_comment)

            # Append True or False depending on whether the action was to
            # open a patch (True) or merge a patch (False)
            gerrit_patch_status[gerrit_patch_id].append(not(bool(merged)))

        for patch in gerrit_patch_status:
            # The normal sequence of GerritBot transactions for a Gerrit change is "Change
            # \d+ had a related patch set uploaded" (indicated by True in
            # gerrit_patch_status) eventually followed by "Change \d+ (merged|abandoned)
            # by whoever" (indicated by False in gerrit_patch_status).  The transactions
            # are returned in reverse order so the opened/merged pattern will appear as
            # the reverse of [True, False], which is [False, True].
            if gerrit_patch_status[patch] != [False, True]:
                return False
        return True


client = Client.newFromCreds()

gerrit_bot_phid = 'PHID-USER-idceizaw6elwiwm5xshb'
project_patch_for_review_phid = 'PHID-PROJ-onnxucoedheq3jevknyr'
checker = Checker(
    gerrit_bot_phid,
    project_patch_for_review_phid,
    client)
gen = client.getTasksWithProject(project_patch_for_review_phid)
for phid in gen:
    if checker.phid_check(phid):
        print(client.taskDetails(phid)['id'])
        try:
            client.removeProjectByPhid(project_patch_for_review_phid, phid)
        except BaseException:
            continue
        time.sleep(10)
