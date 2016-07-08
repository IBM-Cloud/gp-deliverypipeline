#!/usr/bin/python

#***************************************************************************
# Copyright 2015 IBM
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
#***************************************************************************

import json
import logging
import logging.handlers
import os
import os.path
import sys
import time
from subprocess import call, Popen, PIPE
import python_utils

# ascii color codes for output
LABEL_GREEN='\033[0;32m'
LABEL_RED='\033[0;31m'
LABEL_COLOR='\033[0;33m'
LABEL_NO_COLOR='\033[0m'
STARS="**********************************************************************"

GLOBALIZATION_SERVICE='g11n-pipeline'
GLOBALIZATION_SERVICE_PLAN='gp-beta-plan'
DEFAULT_SERVICE=GLOBALIZATION_SERVICE
DEFAULT_SERVICE_PLAN="NONE"
DEFAULT_SERVICE_NAME=DEFAULT_SERVICE


# check cli args, set globals appropriately
def parseArgs ():
    parsedArgs = {}
    parsedArgs['loginonly'] = False
    parsedArgs['cleanup'] = False
    parsedArgs['checkstate'] = False
    for arg in sys.argv:
        if arg == "--loginonly":
            # only login, no scanning or submission
            parsedArgs['loginonly'] = True
        if arg == "--cleanup":
            # cleanup/cancel all complete jobs, and delete irx files
            parsedArgs['cleanup'] = True
        if arg == "--checkstate":
            # just check state of existing jobs, don't scan or submit
            # any new ones
            parsedArgs['checkstate'] = True

    return parsedArgs

def setenvvariable(key, value, filename="setenv_globalization.sh"):
    keyvalue = 'export %s="%s"\n' % (key, value)
    open(filename, 'a+').write(keyvalue)

# begin main execution sequence

try:
    python_utils.LOGGER = python_utils.setup_logging()
    Logger = python_utils.LOGGER
    parsedArgs = parseArgs()
    Logger.info("Getting credentials for Globalization service")
    credentials = python_utils.get_credentials_for_non_binding_service(service=GLOBALIZATION_SERVICE)
    if not (credentials):
        raise Exception("Unable to get credentials for access to the Globalization Pipeline service.")
    url = credentials['url']
    instanceId = credentials['instanceId']
    userId = credentials['userId']
    password = credentials['password']
    if not (url) or not (instanceId) or not (userId) or not (password):
        raise Exception("Unable to get credentials for access to the Globalization Pipeline service.")
    dashboard = python_utils.find_service_dashboard(GLOBALIZATION_SERVICE)
    Logger.info("Target url for Globalization Service is " + url)
    Logger.info("Writing credentials to setenv_globalization.sh")
    setenvvariable('GAAS_ENDPOINT', url)
    setenvvariable('GAAS_INSTANCE_ID', instanceId)
    setenvvariable('GAAS_USER_ID', userId)
    setenvvariable('GAAS_PASSWORD', password)
    setenvvariable('GAAS_DASHBOARD', dashboard)

    # allow testing connection without full job scan and submission
    if parsedArgs['loginonly']:
        Logger.info("LoginOnly set, login complete, exiting")
        sys.exit(0)

except Exception, e:
    Logger.warning("Exception received", exc_info=e)
    sys.exit(1)

