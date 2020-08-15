import requests
import json
import subprocess
import tempfile
import urllib
import os
from contextlib import contextmanager


with open('gerrit-creds.json', 'r') as f:
    creds = json.loads(f.read())

def load_ssh_key():
    mixin = ShellMixin()
    mixin.check_call(['ssh-add', '/home/amsa/Phabricator-maintenance-bot/private_key'])

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
        return f'ssh://{prefix}gerrit.wikimedia.org:29418/{repo}'
    else:
        return f'https://{prefix}gerrit.wikimedia.org/r/{repo}.git'


class ShellMixin:
    def check_call(self, args: list, stdin='', env=None,
                   ignore_returncode=False) -> str:
        debug = self.log if hasattr(self, 'log') else print
        debug('$ ' + ' '.join(args))
        res = subprocess.run(
            args,
            input=stdin.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env
        )
        debug(res.stdout.decode())
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
        self.check_call(['scp', '-p', '-P', '29418', creds['name'] + '@gerrit.wikimedia.org:hooks/commit-msg', '.git/hooks/'])

    def build_push_command(self, options: dict) -> list:
        per = '%topic=new-wikis-patches'
        for hashtag in options['hashtags']:
            per += ',t=' + hashtag
        if options.get('vote'):
            per += ',l=' + options['vote']
            # If we're not automerging, vote V+1 to trigger jenkins (T254070)
        if options.get('message'):
            per += ',m=' + urllib.parse.quote_plus(options['message'])
        return ['git', 'push',
                gerrit_url(options['repo'], creds['name'], ssh=True),
                'HEAD:refs/for/master' + per]

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
            'i18n/wikimediainterwikisearchresults/en.json',
            'i18n/wikimediainterwikisearchresults/qqq.json'
        ]
        for file_ in files:
            with open(file_, 'r') as f:
                result = json.load(f)
            with open(file_, 'w') as f:
                f.write(json.dumps(result, ensure_ascii=False, indent='\t', sort_keys=True))

    def commit(self):
        self.check_call(['git', 'add', '.'])
        with open('.git/COMMIT_EDITMSG', 'w') as f:
            f.write(self.commit_message)
        self.check_call(['git', 'commit', '-F', '.git/COMMIT_EDITMSG'])
        load_ssh_key()
        self.check_call(self.build_push_command({'hashtags': ['automated-wiki-creation'], 'repo': self.name}))

gerritbot = GerritBot('mediawiki/extensions/WikimediaMessages', "Order entries by alphabetical order\n\nThis would make creating automated patches easier")
gerritbot.run()