import base64
import json
import re
import socket

import requests

from lib import Client

final_text = ''
gerrit_path = 'https://gerrit.wikimedia.org/g/'
client = Client.newFromCreds()


def add_text(a):
    global final_text
    final_text += a + '\n'


def get_file_from_gerrit(path):
    gerrit_url = 'https://gerrit.wikimedia.org/g/'
    url = gerrit_url + '{0}?format=TEXT'.format(path)
    r = requests.get(url)
    if r.status_code == 200:
        return base64.b64decode(r.text).decode('utf-8')
    else:
        return ''


def hostname_resolves(hostname):
    try:
        socket.gethostbyname(hostname)
    except socket.error:
        return False
    return True

def handle_special_wiki_apache(parts):
    apache_file = get_file_from_gerrit('operations/puppet/+/production/modules/mediawiki/manifests/web/prod_sites.pp')
    url = '.'.join(parts)
    return url in apache_file


def post_a_comment(comment):
    comment = 'Hello, I am helping on creating this wiki. ' + comment + \
              ' ^_^ Sincerely, your Fully Automated Resource Tackler'
    pass


def create_subticket(text, projects, task_phid):
    pass


def create_non_special_wikis_dns_subticket(parts, task_details):
    pass


def create_special_wikis_dns_subticket(parts, task_details):
    pass


def handle_subticket_for_cloud(ticket_phid, task_details, db_name):
    pass


def create_apache_config_subticket(parts, task_details):
    pass

def get_dummy_wiki(shard, family):
    if family == "wiktionary":
        return {
            "s3": "aawiki"
        }.get(shard, "?????")
    else:
        return {
            #"s3": "aawiki",
            "s5": "cebwiki" # TODO: Change this to muswiki once T259004 is done
        }.get(shard, "?????")


def hande_task(phid):
    global final_text
    final_text = ''
    task_details = client.taskDetails(phid)
    print('Checking T%s' % task_details['id'])
    add_text('\n\n------\n**Pre-install automatic checklist:**')
    language_code = re.findall(r'\n- *?\*\*Language code:\*\* *?(\S+)', task_details['description'])
    if not language_code:
        print('lang code not found, skipping')
        return
    language_code = language_code[0]
    url = re.findall(r'\n- *?\*\*Site URL:\*\* *?(\S+)', task_details['description'])
    if not url:
        print('url not found, skipping')
        return
    url = url[0]
    parts = url.split('.')
    if len(parts) != 3 or parts[2] != 'org':
        print('the url looks weird, skipping')
        return
    shard = re.findall(r'\n- *?\*\*Shard:\*\* *?(\S+)', task_details['description'])[0]

    shardDecided = shard != "TBD"
    if shardDecided:
        add_text(' [X] #DBA decided about the shard')
    else:
        add_text(' [] #DBA decided about the shard')

    special = parts[1] == 'wikimedia'
    dns_url = gerrit_path + 'operations/dns/+/master/templates/wikimedia.org' if special else gerrit_path + 'operations/dns/+/master/templates/helpers/langlist.tmpl'

    dns = hostname_resolves(url)
    if not dns:
        add_text(' [] [[{}|DNS]]'.format(dns_url))
        if special:
            create_special_wikis_dns_subticket(parts, task_details)
        else:
            create_non_special_wikis_dns_subticket(parts, task_details)
        post_a_comment('It seems that there is not DNS entry for this wiki, '
                       'I am creaing a subticket, Please make a patch.')
    else:
        add_text(' [x] [[{}|DNS]]'.format(dns_url))

    if parts[1] == 'wikipedia':
        db_name = parts[0].replace('-', '_') + 'wiki'
    else:
        db_name = parts[0].replace('-', '_') + parts[1]

    handle_subticket_for_cloud(client.lookupPhid('T251371'), task_details, db_name)

    if special:
        apache_url = gerrit_path + 'operations/puppet/+/master/modules/mediawiki/manifests/web/prod_sites.pp'
        if not handle_special_wiki_apache(parts):
            apache = False
            add_text(' [] [[{}|Apache config]]'.format(apache_url))
            create_apache_config_subticket(parts, task_details)
        else:
            apache = True
            add_text(' [x] [[{}|Apache config]]'.format(apache_url))
    else:
        apache = True
        add_text(' [x] Apache config (Not needed)')

    langdb_url = 'https://raw.githubusercontent.com/wikimedia/language-data/master/data/langdb.yaml'
    r = requests.get(langdb_url)
    if re.search(r'\n *?' + language_code + ':', r.text):
        langdb = True
        add_text(' [x] [[{}|Language configuration in language data repo]]'.format(langdb_url))
    else:
        langdb = False
        add_text(' [] [[{}|Language configuration in language data repo]]'.format(langdb_url))

    core_messages_url = 'https://raw.githubusercontent.com/wikimedia/mediawiki/master/languages/messages/Messages{}.php'.format(
        language_code[0].upper() + language_code[1:]
    )
    r = requests.get(core_messages_url)
    if r.status_code == 200:
        core_lang = True
        add_text(' [x] [[{}|Language configuration in mediawiki core]]'.format(core_messages_url))
    else:
        core_lang = False
        add_text(' [] [[{}|Language configuration in mediawiki core]]'.format(core_messages_url))
    path = 'mediawiki/extensions/WikimediaMessages/+/master/i18n/wikimediaprojectnames/en.json'
    wikimedia_messages_data = get_file_from_gerrit(path)
    wikimedia_messages_data = json.loads(wikimedia_messages_data)
    if 'project-localized-name-' + db_name in wikimedia_messages_data:
        wikimedia_messages_one = True
        add_text(' [x] [[{}|Wikimedia messages configuration]]'.format(gerrit_path + path))
    else:
        wikimedia_messages_one = False
        add_text(' [] [[{}|Wikimedia messages configuration]]'.format(gerrit_path + path))
    url = 'https://en.wikipedia.org/wiki/MediaWiki:Project-localized-name-' + db_name
    r = requests.get(url)
    if 'Wikipedia does not have a' not in r.text:
        wikimedia_messages_one_deployed = True
        add_text('  [x] [[{}|deployed]]'.format(url))
    else:
        wikimedia_messages_one_deployed = False
        add_text('  [] [[{}|deployed]]'.format(url))

    if parts[1] == 'wikipedia':
        path = 'mediawiki/extensions/WikimediaMessages/+/master/i18n/wikimediainterwikisearchresults/en.json'
        search_messages_data = get_file_from_gerrit(path)
        search_messages_data = json.loads(search_messages_data)
        if 'search-interwiki-results-' + db_name in search_messages_data:
            wikimedia_messages_two = True
            add_text(
                ' [x] [[{}|Wikimedia messages (interwiki search result) configuration]]'.format(gerrit_path + path))
        else:
            wikimedia_messages_two = False
            add_text(' [] [[{}|Wikimedia messages (interwiki search result) configuration]]'.format(gerrit_path + path))
        url = 'https://en.wikipedia.org/wiki/MediaWiki:Search-interwiki-results-' + db_name
        r = requests.get(url)
        if 'Wikipedia does not have a' not in r.text:
            wikimedia_messages_two_deployed = True
            add_text('  [x] [[{}|deployed]]'.format(url))
        else:
            wikimedia_messages_two_deployed = False
            add_text('  [] [[{}|deployed]]'.format(url))
    else:
        wikimedia_messages_two = True
        wikimedia_messages_two_deployed = True
        add_text(' [x] Wikimedia messages (interwiki search result) configuration (not needed)')

    if dns and apache and langdb and core_lang and wikimedia_messages_one and wikimedia_messages_one_deployed and wikimedia_messages_two and wikimedia_messages_two_deployed and shardDecided:
        add_text('**The Wiki is ready to be created.**')
    else:
        add_text('**The creation is blocked until these part are all done.**')

    add_text('\n-------\n**Post install automatic checklist:**')

    path = 'mediawiki/services/restbase/deploy/+/master/scap/vars.yaml'
    restbase = get_file_from_gerrit(path)
    if '.'.join(parts) in restbase:
        add_text(' [x] [[{}|RESTbase]]'.format(gerrit_path + path))
    else:
        add_text(' [] [[{}|RESTbase]]'.format(gerrit_path + path))
    path = 'mediawiki/services/cxserver/+/master/config/languages.yaml'
    cxconfig = get_file_from_gerrit(path)
    if '\n- ' + language_code in cxconfig:
        add_text(' [x] [[{}|CX Config]]'.format(gerrit_path + path))
    else:
        add_text(' [] [[{}|CX Config]]'.format(gerrit_path + path))

    path = 'analytics/refinery/+/master/static_data/pageview/whitelist/whitelist.tsv'
    refinery_whitelist = get_file_from_gerrit(path)
    if '.'.join(parts[:2]) in refinery_whitelist:
        add_text(' [x] [[{}|Analytics refinery]]'.format(gerrit_path + path))
    else:
        add_text(' [] [[{}|Analytics refinery]]'.format(gerrit_path + path))

    url = 'pywikibot/core/+/master/pywikibot/families/{}_family.py'.format(parts[1])
    pywikibot = get_file_from_gerrit(url)
    if "'{}'".format(language_code) in pywikibot:
        add_text(' [x] [[{}|Pywikibot]]'.format(gerrit_path + url))
    else:
        add_text(' [] [[{}|Pywikibot]]'.format(gerrit_path + url))

    url = 'https://www.wikidata.org/w/api.php?action=help&modules=wbgetentities'
    wikiata_help_page = requests.get(url).text
    if db_name in wikiata_help_page:
        add_text(' [x] [[{}|Wikidata]]'.format(url))
    else:
        add_text(' [] [[{}|Wikidata]]'.format(url))

    add_text(' [] Import from Incubator')
    add_text(' [] Clean up old interwiki links')
    add_text('\n-------')
    add_text('**Step by step commands**:')
    dummy_wiki = get_dummy_wiki("s3", parts[1])
    add_text('On deploy1001:')
    add_text('`cd /srv/mediawiki-staging/`')
    add_text('`git fetch`')
    add_text('`git log -p HEAD..@{u}`')
    add_text('`git rebase`')
    add_text('On mwmaint1002:')
    add_text('`scap pull`')
    add_text('`mwscript extensions/WikimediaMaintenance/addWiki.php --wiki={dummy} {lang} {family} {db} {url}`'.format(
        dummy=dummy_wiki, lang=language_code, family=parts[1], db=db_name, url='.'.join(parts)
    ))
    summary = 'Creating {db_name} ({phab})'.format(db_name=db_name, phab='T' + task_details['id'])
    add_text('On deploy1001:')
    add_text('`scap sync-file dblists "{}"`'.format(summary))
    add_text('`scap sync-wikiversions "{}"`'.format(summary))
    if parts[1] == 'wikimedia':
        add_text('`scap sync-file multiversion/MWMultiVersion.php "{}"`'.format(summary))
    add_text('`scap sync-file static/images/project-logos/ "{}"`'.format(summary))
    add_text('`scap sync-file wmf-config/InitialiseSettings.php "{}"`'.format(summary))
    if parts[1] != 'wikimedia':
        add_text('`scap sync-file langlist "{}"`'.format(summary))
    add_text('`scap update-interwiki-cache`')
    add_text('\n**End of automatic output**')
    old_report = re.findall(
        r'(\n\n------\n\*\*Pre-install automatic checklist:\*\*.+?\n\*\*End of automatic output\*\*\n)',
        task_details['description'], re.DOTALL)
    if not old_report:
        print('old report not found, appending')
        client.setTaskDescription(task_details['phid'], task_details['description'] + final_text)
    else:
        if old_report[0] != final_text:
            print('Updating old report')
            client.setTaskDescription(task_details['phid'],
                                      task_details['description'].replace(old_report[0], final_text))


def main():
    open_create_wikis_phid = 'PHID-PROJ-kmpu7gznmc2edea3qn2x'
    for phid in client.getTasksWithProject(open_create_wikis_phid, statuses=['open']):
        hande_task(phid)


main()
