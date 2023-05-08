import re
import time
from collections import defaultdict

from lib import Client


class Checker():
    def __init__(self, gerrit_bot_phid, code_review_bot_phid, project_patch_for_review_phid, client):
        self.gerrit_bot_phid = gerrit_bot_phid
        self.code_review_bot_phid = code_review_bot_phid
        self.project_patch_for_review_phid = project_patch_for_review_phid
        self.client = client

    def check(self, t_id):
        """
        Returns true if the Patch-For-Review project should be removed from the Phabricator
        task identified 't_id'.
        """
        phid = self.client.lookupPhid(t_id)
        return self.phid_check(phid)

    def get_change_url(self, raw_comment):
        m = re.search(r'https://gerrit(?:-test|)\.wikimedia\.org/r/\d+', raw_comment)
        if m:
            return m[0]
        m = re.search(r'https://gitlab\.wikimedia\.org/repos/.*/-/merge_requests/\d+', raw_comment)
        if m:
            return m[0]
        return None

    def get_operation_type(self, raw_comment, url):
        """
        If the operation type can be determined from raw_comment, return
        it.  It will be the string "open" (first patchset created or merge
        request created) or "close" (merge or abandon)
        """
        # Gitlab style
        if re.search(r"opened " + re.escape(url), raw_comment):
            return "open"

        if re.search(r"(merged|closed) " + re.escape(url), raw_comment):
            return "close"

        # Gerrit style
        if re.search(r"Change \d+ had a related patch set uploaded", raw_comment):
            return "open"

        if re.search(r'Change \d+ \*\*(?:merged|abandoned)\*\* by ', raw_comment):
            return "close"

        return None

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
            if transaction['authorPHID'] in [self.gerrit_bot_phid, self.code_review_bot_phid]:
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

            change_url = self.get_change_url(raw_comment)
            if change_url:
                op = self.get_operation_type(raw_comment, change_url)

                # Append True or False depending on whether the action was to
                # open/reopen a change (True) or merge a change (False)
                gerrit_patch_status[change_url].append(op in ["open", "reopen"])

        for patch in gerrit_patch_status:
            # The normal sequence of GerritBot transactions for a Gerrit change is "Change
            # \d+ had a related patch set uploaded" (indicated by True in
            # gerrit_patch_status) eventually followed by "Change \d+ (merged|abandoned)
            # by whoever" (indicated by False in gerrit_patch_status).  The transactions
            # are returned in reverse order so the opened/merged pattern will appear as
            # the reverse of [True, False], which is [False, True].
            # FIXME: This logic can't handle a open/close/reopen/merge situation.
            if gerrit_patch_status[patch] != [False, True]:
                return False
        return True

if __name__ == "__main__":
    client = Client.newFromCreds()

    gerrit_bot_phid = 'PHID-USER-idceizaw6elwiwm5xshb'
    code_review_bot_phid = 'PHID-USER-ckazlx2gejbyo75y6lid'
    project_patch_for_review_phid = 'PHID-PROJ-onnxucoedheq3jevknyr'
    checker = Checker(
        gerrit_bot_phid,
        code_review_bot_phid,
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
