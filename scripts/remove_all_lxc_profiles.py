#!/usr/bin/env python3


import subprocess
import re

result = subprocess.run(['lxc', 'profile', 'list'], stdout=subprocess.PIPE)

for profile_line in result.stdout.decode('utf-8').split('\n'):
#    print(profile_line)
    match = re.search(r"juju-(([a-zA-Z0-9])+-)*[a-zA-Z0-9]*", profile_line)
    if match is not None:
        profile = match.group()
        print("[INFO] Deleting profile %s" % profile)
        subprocess.run(['lxc', 'profile', 'delete', profile])
