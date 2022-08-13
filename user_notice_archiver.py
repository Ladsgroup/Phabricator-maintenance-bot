from lib import Client


client = Client.newFromCreds()

user_notice_phid = client.lookupPhid('#user-notice')
columns = client.getColumns(user_notice_phid)
mapping = {}
for column in columns['data']:
    mapping[column['fields']['name']] = column['phid']
gen = client.getInactiveTasksWithProject(user_notice_phid, columns=[mapping['Already announced/Archive']])
for phid in gen:
    client.changeProjectByPhid(phid, user_notice_phid, 'PHID-PROJ-y6egyt5y4lvnzs5mgll6')
