#!/usr/bin/env python

#********************************************************************************
# Copyright 2017 IBM
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#********************************************************************************

import os
import urllib2
import json
import sys

if len(sys.argv) < 2:
    raise Exception('Must supply a command to run.\nUsage: %s <cmd> ...' % sys.argv[0])

fakebroker = os.environ.get('GP_FAKE_BROKER')
if not fakebroker:
    raise Exception('Error: GP_FAKE_BROKER must be set.')
fetcher = urllib2.urlopen(fakebroker)
credsjson = fetcher.read()
creds = json.loads(credsjson)

GAAS_ENDPOINT = os.environ['GAAS_ENDPOINT'] = ( creds["credentials"]["url"] + '/rest' )
GAAS_USER_ID = os.environ['GAAS_USER_ID'] = creds["credentials"]["userId"]
GAAS_INSTANCE_ID = os.environ['GAAS_INSTANCE_ID'] = creds["credentials"]["instanceId"]
GAAS_PASSWORD = os.environ['GAAS_PASSWORD'] = creds["credentials"]["password"]

print "# GAAS_INSTANCE_ID=%s, timeout=%d ms" % (GAAS_INSTANCE_ID, creds["timeout"])
#print creds
print "# Exec %s" % str(sys.argv[1:])
os.execvp(sys.argv[1], sys.argv[1:])

