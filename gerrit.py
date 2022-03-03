"""
Copyright (C) 2019 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.
You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import os
import subprocess
import tempfile
import urllib
from contextlib import contextmanager

import requests

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, 'gerrit-creds.json'), 'r') as f:
    creds = json.loads(f.read())


def load_ssh_key():
    mixin = ShellMixin()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    mixin.check_call(
        ['ssh-add', os.path.join(dir_path, 'private_key')])


@contextmanager
def cd(dirname):
    cwd = os.getcwd()
    os.chdir(dirname)
    try:
        yield dirname
    finally:
        os.chdir(cwd)


def gerrit_url(repo: str, user=None, ssh=False) -> str:
    if user is not None:
        prefix = user + '@'
    else:
        prefix = ''
    if ssh:
        return 'ssh://{}gerrit.wikimedia.org:29418/{}'.format(prefix, repo)
    else:
        return 'https://{}gerrit.wikimedia.org/r/{}.git'.format(prefix, repo)


class ShellMixin:
    def check_call(self, args: list, stdin='', env=None,
                   ignore_returncode=False) -> str:
        debug = self.log if hasattr(self, 'log') else print
        #debug('$ ' + ' '.join(args))
        res = subprocess.run(
            args,
            input=stdin.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env
        )
        # debug(res.stdout.decode())
        if not ignore_returncode:
            res.check_returncode()
        return res.stdout.decode()

    def clone(self, repo):
        url = gerrit_url(repo, user=creds['name'])
        self.check_call(['git', 'clone', url, 'repo', '--depth=1'])
        os.chdir('repo')
        self.check_call(['git', 'config', 'user.name', creds['name']])
        self.check_call(['git', 'config', 'user.email', creds['email']])
        self.check_call(['git', 'submodule', 'update', '--init'])
        load_ssh_key()
        self.check_call(['scp', '-p', '-P', '29418', creds['name'] +
                         '@gerrit.wikimedia.org:hooks/commit-msg', '.git/hooks/'])

    def build_push_command(self, options: dict) -> list:
        per = '%topic=new-wikis-patches'
        for hashtag in options['hashtags']:
            per += ',t=' + hashtag
        if options.get('vote'):
            per += ',l=' + options['vote']
            # If we're not automerging, vote V+1 to trigger jenkins (T254070)
        if options.get('message'):
            per += ',m=' + urllib.parse.quote_plus(options['message'])
        branch = options.get('branch', 'master')
        return ['git', 'push',
                gerrit_url(options['repo'], creds['name'], ssh=True),
                'HEAD:refs/for/' + branch + per]


class GerritBot(ShellMixin):
    def __init__(self, name, commit_message):
        self.name = name
        self.commit_message = commit_message

    def run(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            with cd(tmpdirname):
                self.clone(self.name)
                self.changes()
                self.commit()

    def changes(self):
        files = [
            'i18n/wikimediaprojectnames/en.json',
            'i18n/wikimediaprojectnames/qqq.json'
        ]
        for file_ in files:
            with open(file_, 'r') as f:
                result = json.load(f)
            with open(file_, 'w') as f:
                f.write(json.dumps(result, ensure_ascii=False,
                                   indent='\t', sort_keys=True))

    def commit(self):
        self.check_call(['git', 'add', '.'])
        with open('.git/COMMIT_EDITMSG', 'w') as f:
            f.write(self.commit_message)
        self.check_call(['git', 'commit', '-F', '.git/COMMIT_EDITMSG'])
        self.check_call(self.build_push_command(
            {'hashtags': ['automated-wiki-creation'], 'repo': self.name}))


if __name__ == "__main__":
    gerritbot = GerritBot('mediawiki/extensions/WikimediaMessages',
                          "Order entries by alphabetical order\n\nThis would make creating automated patches easier")
    gerritbot.run()
