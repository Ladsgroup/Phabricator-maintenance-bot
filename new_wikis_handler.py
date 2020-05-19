import base64
import json
import re
import sys

import requests

from lib import Client


def get_file_from_gerrit(path):
    gerrit_url = 'https://gerrit.wikimedia.org/g/'
    url = gerrit_url + '{0}?format=TEXT'.format(path)
    return base64.b64decode(requests.get(url).text).decode('utf-8')


def handle_non_special_wikis(parts, language_code):
    if language_code != parts[0]:
        return
    dns_file = get_file_from_gerrit('operations/dns/+/master/templates/helpers/langlist.tmpl')
    return f"'{language_code}'" in dns_file


def handle_special_wiki_dns(parts):
    dns_file = get_file_from_gerrit('operations/dns/+/master/templates/wikimedia.org')
    name = parts[0]
    return f"\n{name}" in dns_file


def handle_special_wiki_apache(parts):
    apache_file = get_file_from_gerrit('operations/puppet/+/master/modules/mediawiki/manifests/web/prod_sites.pp')
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


def main():
    print('\n------\n**Pre-install automatic checklist:**')
    client = Client.newFromCreds()
    gerrit_path = 'https://gerrit.wikimedia.org/g/'
    task_details = client.taskDetails(client.lookupPhid(sys.argv[2]))
    language_code = re.findall(r'\n- *?\*\*Language code:\*\* *?(\S+)', task_details['description'])
    if not language_code:
        return
    language_code = language_code[0]
    url = re.findall(r'\n- *?\*\*Site URL:\*\* *?(\S+)', task_details['description'])
    if not url:
        return
    url = url[0]
    parts = url.split('.')
    if len(parts) != 3 or parts[2] != 'org':
        return
    if parts[1] == 'wikimedia':
        dns = handle_special_wiki_dns(parts)
        special = True
        dns_url = gerrit_path + 'operations/dns/+/master/templates/wikimedia.org'

    else:
        dns = handle_non_special_wikis(parts, language_code)
        dns_url = gerrit_path + 'operations/dns/+/master/templates/helpers/langlist.tmpl'
        special = False
    if not dns:
        print(' [] [[{}|DNS]]'.format(dns_url))
        if special:
            create_special_wikis_dns_subticket(parts, task_details)
        else:
            create_non_special_wikis_dns_subticket(parts, task_details)
        post_a_comment('It seems that there is not DNS entry for this wiki, '
                       'I am creaing a subticket, Please make a patch.')
    else:
        print(' [x] [[{}|DNS]]'.format(dns_url))

    if parts[1] == 'wikipedia':
        db_name = language_code + 'wiki'
    else:
        db_name = language_code + parts[1]

    handle_subticket_for_cloud(client.lookupPhid('T251371'), task_details, db_name)

    if special:
        apache_url = gerrit_path + 'operations/puppet/+/master/modules/mediawiki/manifests/web/prod_sites.pp'
        if not handle_special_wiki_apache(parts):
            apache = False
            print(' [] [[{}|Apache config]]'.format(apache_url))
            create_apache_config_subticket(parts, task_details)
        else:
            apache = True
            print(' [x] [[{}|Apache config]]'.format(apache_url))
    else:
        apache = True
        print(' [x] Apache config (Not needed)')

    langdb_url = 'https://raw.githubusercontent.com/wikimedia/language-data/master/data/langdb.yaml'
    r = requests.get(langdb_url)
    if re.search(r'\n *?' + language_code + ':', r.text):
        langdb = True
        print(' [x] [[{}|Language configuration in language data repo]]'.format(langdb_url))
    else:
        langdb = False
        print(' [] [[{}|Language configuration in language data repo]]'.format(langdb_url))

    core_messages_url = 'https://raw.githubusercontent.com/wikimedia/mediawiki/master/languages/messages/Messages{}.php'.format(
        language_code[0].upper() + language_code[1:]
    )
    r = requests.get(core_messages_url)
    if r.status_code == 200:
        core_lang = True
        print(' [x] [[{}|Language configuration in mediawiki core]]'.format(core_messages_url))
    else:
        core_lang = False
        print(' [] [[{}|Language configuration in mediawiki core]]'.format(core_messages_url))

    path = 'mediawiki/extensions/WikimediaMessages/+/master/i18n/wikimediaprojectnames/en.json'
    wikimedia_messages_data = get_file_from_gerrit(path)
    wikimedia_messages_data = json.loads(wikimedia_messages_data)
    if 'project-localized-name-' + db_name in wikimedia_messages_data:
        wikimedia_messages_one = True
        print(' [x] [[{}|Wikimedia messages configuration]]'.format(gerrit_path + path))
    else:
        wikimedia_messages_one = False
        print(' [] [[{}|Wikimedia messages configuration]]'.format(gerrit_path + path))
    url = 'https://en.wikipedia.org/wiki/MediaWiki:Project-localized-name-' + db_name
    r = requests.get(url)
    if 'Wikipedia does not have a' not in r.text:
        wikimedia_messages_one_deployed = True
        print('  [x] [[{}|deployed]]'.format(url))
    else:
        wikimedia_messages_one_deployed = False
        print('  [] [[{}|deployed]]'.format(url))

    if parts[1] == 'wikipedia':
        path = 'mediawiki/extensions/WikimediaMessages/+/master/i18n/wikimediainterwikisearchresults/en.json'
        search_messages_data = get_file_from_gerrit(path)
        search_messages_data = json.loads(search_messages_data)
        if 'search-interwiki-results-' + db_name in search_messages_data:
            wikimedia_messages_two = True
            print(' [x] [[{}|Wikimedia messages (interwiki search result) configuration]]'.format(gerrit_path + path))
        else:
            wikimedia_messages_two = False
            print(' [] [[{}|Wikimedia messages (interwiki search result) configuration]]'.format(gerrit_path + path))
        url = 'https://en.wikipedia.org/wiki/MediaWiki:Search-interwiki-results-' + db_name
        r = requests.get(url)
        if 'Wikipedia does not have a' not in r.text:
            wikimedia_messages_two_deployed = True
            print('  [x] [[{}|deployed]]'.format(url))
        else:
            wikimedia_messages_two_deployed = False
            print('  [] [[{}|deployed]]'.format(url))
    else:
        wikimedia_messages_two = True
        wikimedia_messages_two_deployed = True
        print(' [x] Wikimedia messages (interwiki search result) configuration (not needed)')

    if dns and apache and langdb and core_lang and wikimedia_messages_one and wikimedia_messages_one_deployed and wikimedia_messages_two and wikimedia_messages_two_deployed:
        print('**The Wiki is ready to be created.**')
    else:
        print('**The creation is blocked until these part are all done.**')

    print('\n-------\n**Post install automatic checklist:**')

    path = 'mediawiki/services/restbase/deploy/+/master/scap/vars.yaml'
    restbase = get_file_from_gerrit(path)
    if '.'.join(parts) in restbase:
        print(' [x] [[{}|RESTbase]]'.format(gerrit_path + path))
    else:
        print(' [] [[{}|RESTbase]]'.format(gerrit_path + path))
    path = 'mediawiki/services/cxserver/+/master/config/languages.yaml'
    cxconfig = get_file_from_gerrit(path)
    if '\n- ' + language_code in cxconfig:
        print(' [x] [[{}|CX Config]]'.format(gerrit_path + path))
    else:
        print(' [] [[{}|CX Config]]'.format(gerrit_path + path))

    path = 'analytics/refinery/+/master/static_data/pageview/whitelist/whitelist.tsv'
    refinery_whitelist = get_file_from_gerrit(path)
    if '.'.join(parts[:2]) in refinery_whitelist:
        print(' [x] [[{}|Analytics refinery]]'.format(gerrit_path + path))
    else:
        print(' [] [[{}|Analytics refinery]]'.format(gerrit_path + path))

    url = 'pywikibot/core/+/master/pywikibot/families/{}_family.py'.format(parts[1])
    pywikibot = get_file_from_gerrit(url)
    if f"'{language_code}'" in pywikibot:
        print(' [x] [[{}|Pywikibot]]'.format(gerrit_path + url))
    else:
        print(' [] [[{}|Pywikibot]]'.format(gerrit_path + url))

    url = 'https://www.wikidata.org/w/api.php?action=help&modules=wbgetentities'
    wikiata_help_page = requests.get(url).text
    if db_name in wikiata_help_page:
        print(' [x] [[{}|Wikidata]]'.format(url))
    else:
        print(' [] [[{}|Wikidata]]'.format(url))

    print(' [] Import from Incubator')
    print(' [] Clean up old interwiki links')


main()
