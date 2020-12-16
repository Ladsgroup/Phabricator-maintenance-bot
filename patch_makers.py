import json
from datetime import date

from gerrit import GerritBot


class WikimediaMessagesPatchMaker(GerritBot):
    def __init__(self, db_name, english_name, url, lang, bug_id):
        self.db_name = db_name
        self.english_name = english_name
        self.wiki_url = url
        self.wiki_lang = lang
        super().__init__(
            'mediawiki/extensions/WikimediaMessages',
            'Add messages for {} ({})\n\nBug:{}'.format(
                english_name, db_name, bug_id)
        )

    def changes(self):
        file_ = 'i18n/wikimediaprojectnames/en.json'
        result = self._read_json(file_)
        result['project-localized-name-' + self.db_name] = self.english_name
        self._write_json(file_, result)

        file_ = 'i18n/wikimediaprojectnames/qqq.json'
        result = self._read_json(file_)
        result['project-localized-name-' + self.db_name] = '{{ProjectNameDocumentation|url=https://' + \
            self.wiki_url + '|name=' + self.english_name + \
            '|language=' + self.wiki_lang + '}}'
        self._write_json(file_, result)

        if not 'wikipedia' in self.wiki_url:
            return

        file_ = 'i18n/wikimediainterwikisearchresults/en.json'
        result = self._read_json(file_)
        result['search-interwiki-results-' +
               self.db_name] = 'Showing results from [[:{}:|{}]].'.format(self.wiki_lang, self.english_name)
        self._write_json(file_, result)

        file_ = 'i18n/wikimediainterwikisearchresults/qqq.json'
        result = self._read_json(file_)
        result['search-interwiki-results-' + self.db_name] = 'Search results description for ' + \
            self.english_name + '.\n{{LanguageNameTip|' + self.wiki_lang + '}}'
        self._write_json(file_, result)

    def _read_json(self, path):
        with open(path, 'r') as f:
            result = json.load(f)
        return result

    def _write_json(self, path, content):
        with open(path, 'w') as f:
            f.write(json.dumps(content, ensure_ascii=False,
                               indent='\t', sort_keys=True))


class DnsPatchMaker(GerritBot):
    def __init__(self, lang, bug_id):
        self.wiki_lang = lang
        super().__init__(
            'operations/dns',
            'Add {} to langlist helper\n\nBug:{}'.format(lang, bug_id)
        )

    def changes(self):
        with open('templates/helpers/langlist.tmpl', 'r') as f:
            lines = f.read().split('\n')
        header = []
        langs = []
        footer = []
        for line in lines:
            if not line.startswith(' '):
                if not header:
                    header.append(line)
                else:
                    footer.append(line)
            else:
                langs.append(line)
        langs.append("        '{}',".format(self.wiki_lang))
        langs.sort()
        with open('templates/helpers/langlist.tmpl', 'w') as f:
            f.write('\n'.join(header) + '\n' +
                    '\n'.join(langs) + '\n' + '\n'.join(footer))


class CxPatchMaker(GerritBot):
    def __init__(self, lang, bug_id):
        self.wiki_lang = lang
        super().__init__(
            'mediawiki/services/cxserver',
            'Add {} to languages \n\nBug:{}'.format(lang, bug_id)
        )

    def changes(self):
        with open('config/languages.yaml', 'r') as f:
            lines = f.read().split('\n')[:-1]
        lines.append("- {}".format(self.wiki_lang))
        lines.sort()
        with open('config/languages.yaml', 'w') as f:
            f.write('\n'.join(lines) + '\n')


class AnalyticsPatchMaker(GerritBot):
    def __init__(self, project, bug_id):
        self.project = project
        super().__init__(
            'analytics/refinery',
            'Add {} to pageview whitelist \n\nBug:{}'.format(project, bug_id)
        )

    def changes(self):
        with open('static_data/pageview/whitelist/whitelist.tsv', 'r') as f:
            lines = f.read().split('\n')
        projects = []
        non_projects = []
        for line in lines:
            if line.startswith('project'):
                projects.append(line)
            else:
                non_projects.append(line)
        today = date.today()
        projects.append('project\t{}\t{}'.format(
            self.project,
            today.strftime("%Y-%m-%d 00:00:00")
        ))
        projects = list(set(projects))
        projects.sort()
        with open('static_data/pageview/whitelist/whitelist.tsv', 'w') as f:
            f.write('\n'.join(projects) + '\n' + '\n'.join(non_projects))
