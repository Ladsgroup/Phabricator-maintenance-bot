"""
Adds tasks in configured projects to other configured projects
"""

from lib import Client

rules = [
    {
        # current H175 - see T136921
        'add': 'Design',
        'in': ['WMF-Design', 'WMDE-Design'],
    },
]

client = Client.newFromCreds()

for rule in rules:
    handled_tasks = []

    wanted_project_phid = client.lookupPhid('#' + rule['add'])
    for project_name in rule['in']:
        project_phid = client.lookupPhid('#' + project_name)
        for task_phid in client.getTasksWithProject(project_phid):
            # if a task is in multiple 'in' projects, still only process it once
            if task_phid in handled_tasks:
                continue
            handled_tasks.append(task_phid)

            task = client.taskDetails(task_phid)
            if wanted_project_phid not in task['projectPHIDs']:
                client.addTaskProject(task_phid, wanted_project_phid)
