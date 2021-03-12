from lib import Client


class Checker():
    def __init__(self, work, client):
        self.work = work
        self.client = client

    def phid_check(self, phid):
        if self.work.get('projects'):
            return self.phid_check_project(
                phid, [
                    self.client.lookupPhid(
                        '#' + i) for i in self.work['projects']])
        if self.work.get('status'):
            return self.phid_check_status(phid, self.work['status'])
        return False

    def phid_check_project(self, phid, project_phids):
        taskDetails = self.client.taskDetails(phid)
        for project_phid in project_phids:
            if project_phid in taskDetails['projectPHIDs']:
                return True
        return False

    def phid_check_status(self, phid, statuses):
        taskDetails = self.client.taskDetails(phid)
        return taskDetails['statusName'] in statuses


client = Client.newFromCreds()

work = [{'from': ['incoming'],
         'project': 'Wikidata',
         'to': 'in progress',
         'projects': ['wikidata-campsite-iteration-∞',
                      'Wikibase_Extension_Decoupling_and_Registration',
                      'wikidata-bridge-sprint-8']},
        {'from': ['Test (Verification)'],
         'project': 'wikidata-campsite-iteration-∞',
         'to': 'Done',
         'status': ['Resolved']},
        {'from': ['Incoming'],
         'project': 'User-Ladsgroup',
         'to': 'In progress',
         'projects': ['wikidata-campsite-iteration-∞',
                      'RL_Module_Terminators_Trailblazing']},
        {'from': ['In progress',
                  'Incoming'],
         'project': 'User-Ladsgroup',
         'to': 'Done',
         'status': ['Resolved']},
        {'from': ['Radar',
                  'Miraheze-Linked',
                  'Extensions & Core',
                  'Configuration'],
         'project': 'User-RhinosF1',
         'to': 'Done',
         'status': ['Resolved']},
        ]
for case in work:
    gen = client.getTasksWithProject(client.lookupPhid('#' + case['project']))
    checker = Checker(case, client)
    columns = client.getColumns(client.lookupPhid('#' + case['project']))
    mapping = {}
    for column in columns['data']:
        mapping[column['fields']['name']] = column['phid']
    for phid in gen:
        if checker.phid_check(phid):
            project_phid = client.lookupPhid('#' + case['project'])
            currentColumnName = client.getTaskColumns(
                phid)['boards'][project_phid]['columns'][0]['name']
            if currentColumnName not in case['from']:
                continue
            try:
                print(phid)
                client.moveColumns(phid, mapping[case['to']])
            except KeyboardInterrupt:
                continue
