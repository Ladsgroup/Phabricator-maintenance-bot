#!/bin/bash

eval $(ssh-agent)
python3 /data/project/phabbot/phabbot/new_wikis_handler.py /data/project/phabbot/phabbot/creds.json 10000000
pkill -u $USER ssh-agent
