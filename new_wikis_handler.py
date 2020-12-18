import base64
import json
import re
import socket

import requests

from lib import Client
from patch_makers import (AnalyticsPatchMaker, CxPatchMaker, DnsPatchMaker,
                          WikimediaMessagesPatchMaker)

final_text = ''
gerrit_path = 'https://gerrit.wikimedia.org/g/'
client = Client.newFromCreds()


def add_text(a):
    global final_text
    final_text += a + '\n'


def add_checklist(url, text, checked):
    if checked:
        add_text(' [x] [[{}|{}]]'.format(url, text))
    else:
        add_text(' [] [[{}|{}]]'.format(url, text))


def get_file_from_gerrit(path):
    gerrit_url = 'https://gerrit.wikimedia.org/g/'
    url = gerrit_url + '{0}?format=TEXT'.format(path)
    r = requests.get(url)
    if r.status_code == 200:
        return base64.b64decode(r.text).decode('utf-8')
    else:
        return ''


def get_gerrit_path(repo, filename):
    return repo + '/+/master/' + filename


def get_github_url(repo, filename):
    return 'https://raw.githubusercontent.com/wikimedia/{}/master/{}'.format(
        repo, filename
    )


def hostname_resolves(hostname):
    try:
        socket.gethostbyname(hostname)
    except socket.error:
        return False
    return True


def handle_restbase(url, phid, create_tickets, db_name):
    path = get_gerrit_path(
        'mediawiki/services/restbase/deploy',
        'scap/vars.yaml'
    )
    restbase = get_file_from_gerrit(path)
    add_checklist(gerrit_path + path, 'RESTbase', url in restbase)
    if url in restbase:
        return
    if create_tickets:
        client.createParentTask(
            'Per https://wikitech.wikimedia.org/wiki/Add_a_wiki once the wiki has been created',
            ['PHID-PROJ-mszihytuo3ij3fcxcxgm'],
            phid,
            'Add {} to RESTBase'.format(db_name))


def handle_cx(language_code, bug_id):
    path = get_gerrit_path(
        'mediawiki/services/cxserver',
        'config/languages.yaml'
    )
    cxconfig = get_file_from_gerrit(path)
    cx = '\n- ' + language_code in cxconfig
    add_checklist(gerrit_path + path, 'CX Config', cx)
    if cx:
        return

    r = requests.get(
        'https://gerrit.wikimedia.org/r/changes/'
        '?q=bug:{}+project:mediawiki/services/cxserver'.format(bug_id))
    b = json.loads('\n'.join(r.text.split('\n')[1:]))
    if b:
        return
    maker = CxPatchMaker(language_code, bug_id)
    maker.run()


def handle_analytics(url, bug_id):
    path = get_gerrit_path(
        'analytics/refinery',
        'static_data/pageview/whitelist/whitelist.tsv'
    )
    refinery_whitelist = get_file_from_gerrit(path)
    add_checklist(gerrit_path + path, 'Analytics refinery',
                  url in refinery_whitelist)
    if url in refinery_whitelist:
        return

    r = requests.get(
        'https://gerrit.wikimedia.org/r/changes/'
        '?q=bug:{}+project:analytics/refinery'.format(bug_id))
    b = json.loads('\n'.join(r.text.split('\n')[1:]))
    if b:
        return
    maker = AnalyticsPatchMaker(url, bug_id)
    maker.run()


def handle_pywikibot(family, language_code, create_tickets, db_name, phid):
    path = get_gerrit_path(
        'pywikibot/core',
        'pywikibot/families/{}_family.py'.format(family)
    )
    pywikibot = get_file_from_gerrit(path)
    add_checklist(gerrit_path + path, 'Pywikibot',
                  "'{}'".format(language_code) in pywikibot)
    if create_tickets:
        client.createParentTask(
            'Per https://wikitech.wikimedia.org/wiki/Add_a_wiki once the wiki has been created',
            ['PHID-PROJ-orw42whe2lepxc7gghdq'],
            phid,
            'Add support for {} to Pywikibot'.format(db_name))


def handle_wikidata(db_name, create_tickets, phid):
    url = 'https://www.wikidata.org/w/api.php'
    wikiata_help_page = requests.get(url, params={
        'action': 'help',
        'modules': 'wbgetentities'
    }).text
    add_checklist(url, 'Wikidata', db_name in wikiata_help_page)
    if create_tickets:
        client.createParentTask(
            'Per https://wikitech.wikimedia.org/wiki/Add_a_wiki once the wiki has been created',
            ['PHID-PROJ-egbmgxclscgwu2rbnotm', 'PHID-PROJ-7ocjej2gottz7cikkdc6'],
            phid,
            'Add Wikidata support for {}'.format(db_name))


def handle_special_wiki_apache(parts):
    file_path = 'modules/mediawiki/manifests/web/prod_sites.pp'
    apache_file = get_file_from_gerrit(
        'operations/puppet/+/production/' + file_path)
    url = '.'.join(parts)
    return url in apache_file


def post_a_comment(comment):
    comment = 'Hello, I am helping on creating this wiki. ' + comment + \
              ' ^_^ Sincerely, your Fully Automated Resource Tackler'
    pass


def handle_subticket_for_cloud(task_details, db_name, wiki_status):
    hasSubtasks = client.getTaskSubtasks(task_details['phid'])
    if hasSubtasks:
        return

    client.createSubtask("The new wiki's visibility will be: **%s**." % wiki_status, [
        'PHID-PROJ-hwibeuyzizzy4xzunfsk',  # DBA
        'PHID-PROJ-bj6y6ks7ampcwcignhce'  # Data services
    ], task_details['phid'], 'Prepare and check storage layer for ' + db_name)

def handle_subticket_for_wikistats(task_details, db_name):
    hasSubtasks = client.getTaskSubtasks(task_details['phid'])
    if hasSubtasks:
        return

    client.createSubtask("Please add new wiki `%s` to Wikistats, once it is created. Thanks!" % db_name, [
        'PHID-PROJ-6sht6g4xpdii4c4bga2i' # VPS-project-Wikistats
    ], task_details['phid'], 'Add %s to wikistats' % db_name)


def get_dummy_wiki(shard, family):
    if family == "wiktionary":
        return {
            "s3": "aawiki",
            "s5": "mhwiktionary",
        }.get(shard, "?????")
    else:
        return {
            "s3": "aawiki",
            "s5": "muswiki"
        }.get(shard, "?????")


def create_patch_for_wikimedia_messages(
        db_name, english_name, url, lang, bug_id):
    if not english_name:
        return
    r = requests.get(
        'https://gerrit.wikimedia.org/r/changes/?q='
        'bug:{}+project:mediawiki/extensions/WikimediaMessages'.format(bug_id))
    b = json.loads('\n'.join(r.text.split('\n')[1:]))
    if b:
        return
    maker = WikimediaMessagesPatchMaker(
        db_name, english_name, url, lang, bug_id)
    maker.run()


def handle_dns(special, url, language_code, task_tid):
    dns_path = get_gerrit_path(
        'operations/dns',
        'templates/wikimedia.org' if special else
        'templates/helpers/langlist.tmpl')
    dns_url = gerrit_path + dns_path
    dns = hostname_resolves(url)
    print(url)
    if not dns:
        print('dns not found')
        if not special:
            print('not special')
            create_patch_for_dns(language_code, task_tid)
    add_checklist(dns_url, 'DNS', dns)
    return dns


def handle_apache(special, parts):
    if not special:
        add_text(' [x] Apache config (Not needed)')
        return True

    file_path = 'modules/mediawiki/manifests/web/prod_sites.pp'
    apache_url = gerrit_path + \
                 'operations/puppet/+/production/' + file_path
    if not handle_special_wiki_apache(parts):
        apache = False
    else:
        apache = True
    add_checklist(apache_url, 'Apache config', apache)
    return apache


def handle_langdb(language_code):
    langdb_url = get_github_url('language-data', 'data/langdb.yaml')
    r = requests.get(langdb_url)
    config = 'Language configuration in language data repo'
    if re.search(r'\n *?' + language_code + ':', r.text):
        langdb = True
    else:
        langdb = False
    add_checklist(langdb_url, config, langdb)
    return langdb


def handle_wikimedia_messages_one(
        db_name,
        wiki_spec,
        url,
        language_code,
        task_tid):
    path = get_gerrit_path(
        'mediawiki/extensions/WikimediaMessages',
        'i18n/wikimediaprojectnames/en.json'
    )
    wikimedia_messages_data = get_file_from_gerrit(path)
    wikimedia_messages_data = json.loads(wikimedia_messages_data)
    if 'project-localized-name-' + db_name in wikimedia_messages_data:
        wikimedia_messages_one = True
    else:
        wikimedia_messages_one = False
        english_name = wiki_spec.get('Project name (English)')
        create_patch_for_wikimedia_messages(
            db_name, english_name, url, language_code, task_tid)
    add_checklist(gerrit_path + path,
                  'Wikimedia messages configuration', wikimedia_messages_one)
    url = 'https://en.wikipedia.org/wiki/' + \
          'MediaWiki:Project-localized-name-' + db_name
    r = requests.get(url)
    if 'Wikipedia does not have a' not in r.text:
        wikimedia_messages_one_deployed = True
        add_text('  [x] [[{}|deployed]]'.format(url))
    else:
        wikimedia_messages_one_deployed = False
        add_text('  [] [[{}|deployed]]'.format(url))

    return wikimedia_messages_one and wikimedia_messages_one_deployed


def handle_wikimedia_messages_two(db_name, parts):
    config = 'Wikimedia messages (interwiki search result) configuration'
    if parts[1] != 'wikipedia':
        add_text(' [x] {} (not needed)'.format(config))
        return True

    path = get_gerrit_path(
        'mediawiki/extensions/WikimediaMessages',
        'i18n/wikimediainterwikisearchresults/en.json'
    )
    search_messages_data = json.loads(get_file_from_gerrit(path))
    if 'search-interwiki-results-' + db_name in search_messages_data:
        wikimedia_messages_two = True
    else:
        wikimedia_messages_two = False
    add_checklist(
        gerrit_path + path,
        config,
        wikimedia_messages_two)
    url = 'https://en.wikipedia.org/wiki/' + \
          'MediaWiki:Search-interwiki-results-' + db_name
    r = requests.get(url)
    if 'Wikipedia does not have a' not in r.text:
        wikimedia_messages_two_deployed = True
        add_text('  [x] [[{}|deployed]]'.format(url))
    else:
        wikimedia_messages_two_deployed = False
        add_text('  [] [[{}|deployed]]'.format(url))
    return wikimedia_messages_two and wikimedia_messages_two_deployed


def create_patch_for_dns(lang, bug_id):
    r = requests.get(
        'https://gerrit.wikimedia.org/r/changes/'
        '?q=bug:{}+project:operations/dns'.format(bug_id))
    b = json.loads('\n'.join(r.text.split('\n')[1:]))
    if b:
        return
    maker = DnsPatchMaker(lang, bug_id)
    maker.run()


def handle_core_lang(language_code):
    core_messages_url = get_github_url(
        'mediawiki',
        'languages/messages/Messages{}.php'.format(
            language_code[0].upper() + language_code[1:]))
    r = requests.get(core_messages_url)
    if r.status_code == 200:
        core_lang = True
    else:
        core_lang = False
    add_checklist(core_messages_url,
                  'Language configuration in mediawiki core', core_lang)
    return core_lang


def get_db_name(wiki_spec, parts):
    db_name = wiki_spec.get('Database name')
    if not db_name:
        if parts[1] == 'wikipedia':
            db_name = parts[0].replace('-', '_') + 'wiki'
        else:
            db_name = parts[0].replace('-', '_') + parts[1]
    return db_name


def sync_file(path, summary):
    return '`scap sync-file {} "{}"`'.format(path, summary)


def add_create_instructions(parts, shard, language_code, db_name, task_tid):
    add_text('\n-------')
    add_text('**Step by step commands**:')
    dummy_wiki = get_dummy_wiki(shard, parts[1])
    add_text('On deploy1001:')
    add_text('`cd /srv/mediawiki-staging/`')
    add_text('`git fetch`')
    add_text('`git log -p HEAD..@{u}`')
    add_text('`git rebase`')
    add_text('On mwmaint1002:')
    add_text('`scap pull`')
    addwiki_path = 'mwscript extensions/WikimediaMaintenance/addWiki.php'
    add_text(
        '`{addwiki_path} --wiki={dummy} {lang} {family} {db} {url}`'.format(
            addwiki_path=addwiki_path,
            dummy=dummy_wiki,
            lang=language_code,
            family=parts[1],
            db=db_name,
            url='.'.join(parts)))
    add_text('`{search_path} --wiki={dbname} --cluster=all`'.format(
        search_path='mwscript extensions/CirrusSearch/maintenance/UpdateSearchIndexConfig.php',
        dbname=db_name,
    ))
    summary = 'Creating {db_name} ({phab})'.format(
        db_name=db_name, phab=task_tid)
    add_text('On deploy1001:')
    if shard != "s3":
        add_text(sync_file('wmf-config/db-eqiad.php', summary))
        add_text(sync_file('wmf-config/db-codfw.php', summary))
    add_text(sync_file('dblists', summary))
    add_text('`scap sync-wikiversions "{}"`'.format(summary))
    if parts[1] == 'wikimedia':
        add_text(sync_file('multiversion/MWMultiVersion.php', summary))
    add_text(sync_file('static/images/project-logos/', summary))
    add_text(sync_file('wmf-config/InitialiseSettings.php', summary))
    if parts[1] != 'wikimedia':
        add_text(sync_file('langlist', summary))
    add_text('`scap update-interwiki-cache`')


def update_task_report(task_details):
    global final_text
    if not final_text:
        return
    old_report = re.findall(
        r'(\n\n------\n\*\*Pre-install automatic checklist:'
        r'\*\*.+?\n\*\*End of automatic output\*\*\n)',
        task_details['description'], re.DOTALL)
    if not old_report:
        print('old report not found, appending')
        client.setTaskDescription(
            task_details['phid'], task_details['description'] + final_text)
    else:
        if old_report[0] != final_text:
            print('Updating old report')
            client.setTaskDescription(
                task_details['phid'],
                task_details['description'].replace(
                    old_report[0],
                    final_text))


def hande_task(task_details):
    global final_text
    final_text = ''
    print('Checking T%s' % task_details['id'])
    task_tid = 'T' + task_details['id']

    # Extract wiki config
    wiki_spec = {}
    for case in re.findall(
            r'\n- *?\*\*(.+?):\*\* *?(.+)',
            task_details['description']):
        wiki_spec[case[0].strip()] = case[1].strip()
    language_code = wiki_spec.get('Language code')
    if not language_code:
        print('lang code not found, skipping')
        return
    url = wiki_spec.get('Site URL')
    if not url:
        print('url not found, skipping')
        return
    parts = url.split('.')
    if len(parts) != 3 or parts[2] != 'org':
        print('the url looks weird, skipping')
        return
    db_name = get_db_name(wiki_spec, parts)
    shard = wiki_spec.get('Shard', 'TBD')
    visibility = wiki_spec.get('Visibility', 'unknown')
    shardDecided = shard != "TBD"
    special = parts[1] == 'wikimedia'

    add_text('\n\n------\n**Pre-install automatic checklist:**')
    if shardDecided:
        add_text(' [X] #DBA decided about the shard')
    else:
        add_text(' [] #DBA decided about the shard')
    dns = handle_dns(special, url, language_code, task_tid)
    if not special and wiki_spec.get('Special', '').lower() != 'yes':
        handle_subticket_for_cloud(task_details, db_name, visibility)
        handle_subticket_for_wikistats(task_details, db_name)
    apache = handle_apache(special, parts)
    langdb = handle_langdb(language_code)
    core_lang = handle_core_lang(language_code)
    wm_message_one = handle_wikimedia_messages_one(
        db_name, wiki_spec, url, language_code, task_tid
    )
    wm_message_two = handle_wikimedia_messages_two(db_name, parts)

    if dns and apache and langdb and core_lang and wm_message_one and \
            wm_message_two and shardDecided:
        add_text('**The Wiki is ready to be created.**')
    else:
        add_text('**The creation is blocked until these part are all done.**')

    if visibility.lower() != 'private':
        add_text('\n-------\n**Post install automatic checklist:**')
        create_tickets = client.getTaskParents(task_details['phid'])
        handle_restbase(url, task_details['phid'], not create_tickets, db_name)
        handle_cx(language_code, task_tid)
        handle_analytics('.'.join(parts[:2]), task_tid)
        handle_pywikibot(parts[1], language_code, not create_tickets, db_name, task_details['phid'])
        handle_wikidata(db_name, not create_tickets, task_details['phid'])
        add_text(' [] Import from Incubator')
        add_text(' [] Clean up old interwiki links')
        add_text(' [] Propose the implementation of the standard bot policy')
        add_text(' [] Inform the [[ https://meta.wikimedia.org/wiki/Talk:Countervandalism_Network | CVN ]] project for IRC monitoring')
    add_create_instructions(parts, shard, language_code, db_name, task_tid)
    add_text('\n**End of automatic output**')


def main():
    open_create_wikis_phid = 'PHID-PROJ-kmpu7gznmc2edea3qn2x'
    for phid in client.getTasksWithProject(
            open_create_wikis_phid, statuses=['open']):
        task_details = client.taskDetails(phid)
        hande_task(task_details)
        update_task_report(task_details)


if __name__ == "__main__":
    main()
