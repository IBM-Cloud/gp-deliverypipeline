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

# ascii color codes for output
LABEL_GREEN='\033[0;32m'
LABEL_RED='\033[0;31m'
LABEL_COLOR='\033[0;33m'
LABEL_NO_COLOR='\033[0m'
STARS="**********************************************************************"

GLOBALIZATION_SERVICE='IBM Globalization'
GLOBALIZATION_SERVICE_PLAN='Experimental'
STATIC_ANALYSIS_SERVICE='Static Analyzer'
DEFAULT_SERVICE=STATIC_ANALYSIS_SERVICE
DEFAULT_SERVICE_PLAN="free"
DEFAULT_SERVICE_NAME=DEFAULT_SERVICE
DEFAULT_SCANNAME="staticscan"
DEFAULT_BRIDGEAPP_NAME="pipeline_bridge_app"

Logger=None

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

# setup logmet logging connection if it's available
def setupLogging ():
    logger = logging.getLogger('pipeline')
    if os.environ.get('DEBUG'):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # if logmet is enabled, send the log through syslog as well
    if os.environ.get('LOGMET_LOGGING_ENABLED'):
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        logger.addHandler(handler)
        # don't send debug info through syslog
        handler.setLevel(logging.INFO)

    # in any case, dump logging to the screen
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    if os.environ.get('DEBUG'):
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    return logger

# find the given service in our space, get its service name, or None
# if it's not there yet
def findServiceNameInSpace (service):
    command = "cf services"
    proc = Popen([command], shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if proc.returncode != 0:
        Logger.info("Unable to lookup services, error was: " + out)
        return None

    foundHeader = False
    serviceStart = -1
    serviceEnd = -1
    serviceName = None
    for line in out.splitlines():
        if (foundHeader == False) and (line.startswith("name")):
            # this is the header bar, find out the spacing to parse later
            # header is of the format:
            #name          service      plan   bound apps    last operation
            # and the spacing is maintained for following lines
            serviceStart = line.find("service")
            serviceEnd = line.find("plan")-1
            foundHeader = True
        elif foundHeader:
            # have found the headers, looking for our service
            if service in line:
                # maybe found it, double check by making
                # sure the service is in the right place,
                # assuming we can check it
                if (serviceStart > 0) and (serviceEnd > 0):
                    if service in line[serviceStart:serviceEnd]:
                        # this is the correct line - find the bound app(s)
                        # if there are any
                        serviceName = line[:serviceStart]
                        serviceName = serviceName.strip()
        else:
            continue

    return serviceName

# find a service in our space, and if it's there, get the dashboard
# url for user info on it
def findServiceDashboard (service=DEFAULT_SERVICE):

    serviceName = findServiceNameInSpace(service)
    if serviceName == None:
        return None

    command = "cf service \"" + serviceName + "\""
    proc = Popen([command], shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if proc.returncode != 0:
        return None

    serviceURL = None
    for line in out.splitlines():
        if line.startswith("Dashboard: "):
            serviceURL = line[11:]
        else:
            continue

    return serviceURL

# search cf, find an app in our space bound to the given service, and return
# the app name if found, or None if not
def findBoundAppForService (service=DEFAULT_SERVICE):
    proc = Popen(["cf services"], shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if proc.returncode != 0:
        return None

    foundHeader = False
    serviceStart = -1
    serviceEnd = -1
    boundStart = -1
    boundEnd = -1
    boundApp = None
    for line in out.splitlines():
        if (foundHeader == False) and (line.startswith("name")):
            # this is the header bar, find out the spacing to parse later
            # header is of the format:
            #name          service      plan   bound apps    last operation
            # and the spacing is maintained for following lines
            serviceStart = line.find("service")
            serviceEnd = line.find("plan")-1
            boundStart = line.find("bound apps")
            boundEnd = line.find("last operation")
            foundHeader = True
        elif foundHeader:
            # have found the headers, looking for our service
            if service in line:
                # maybe found it, double check by making
                # sure the service is in the right place,
                # assuming we can check it
                if (serviceStart > 0) and (serviceEnd > 0) and (boundStart > 0) and (boundEnd > 0):
                    if service in line[serviceStart:serviceEnd]:
                        # this is the correct line - find the bound app(s)
                        # if there are any
                        boundApp = line[boundStart:boundEnd]
        else:
            continue

    # if we found a binding, make sure we only care about the first one
    if boundApp != None:
        if boundApp.find(",") >=0 :
            boundApp = boundApp[:boundApp.find(",")]
        boundApp = boundApp.strip()
        if boundApp=="":
            boundApp = None

    if os.environ.get('DEBUG'):
        if boundApp == None:
            Logger.debug("No existing apps found bound to service \"" + service + "\"")
        else:
            Logger.debug("Found existing service \"" + boundApp + "\" bound to service \"" + service + "\"")

    return boundApp

# look for our default bridge app.  if it's not there, create it
def checkAndCreateBridgeApp ():
    # first look to see if the bridge app already exists
    command = "cf apps"
    Logger.debug("Executing command \"" + command + "\"")
    proc = Popen([command], shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if os.environ.get('DEBUG'):
        Logger.debug("command \"" + command + "\" returned with rc=" + str(proc.returncode))
        Logger.debug("\tstdout was " + out)
        Logger.debug("\tstderr was " + err)

    if proc.returncode != 0:
        return None

    for line in out.splitlines():
        if line.startswith(DEFAULT_BRIDGEAPP_NAME + " "):
            # found it!
            return True

    # our bridge app isn't around, create it
    Logger.info("Bridge app does not exist, attempting to create it")
    command = "cf push " + DEFAULT_BRIDGEAPP_NAME + " -i 1 -d mybluemix.net -k 1M -m 64M --no-hostname --no-manifest --no-route --no-start"
    Logger.debug("Executing command \"" + command + "\"")
    proc = Popen([command], shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if os.environ.get('DEBUG'):
        Logger.debug("command \"" + command + "\" returned with rc=" + str(proc.returncode))
        Logger.debug("\tstdout was " + out)
        Logger.debug("\tstderr was " + err)

    if proc.returncode != 0:
        Logger.info("Unable to create bridge app, error was: " + out)
        return False

    return True


# look for our bridge app to bind this service to.  If it's not there,
# attempt to create it.  Then bind the service to that app.  If it 
# all works, return that app name as the bound app
def createBoundAppForService (service=DEFAULT_SERVICE, plan=DEFAULT_SERVICE_PLAN):

    if not checkAndCreateBridgeApp():
        return None

    # look to see if we have the service in our space
    serviceName = findServiceNameInSpace(service)

    # if we don't have the service name, means the tile isn't created in our space, so go
    # load it into our space if possible
    if serviceName == None:
        Logger.info("Service \"" + service + "\" is not loaded in this space, attempting to load it")
        serviceName = service
        command = "cf create-service \"" + service + "\" \"" + plan + "\" \"" + serviceName + "\""
        Logger.debug("Executing command \"" + command + "\"")
        proc = Popen([command], 
                     shell=True, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate();

        if proc.returncode != 0:
            Logger.info("Unable to create service in this space, error was: " + out)
            return None

    # now try to bind the service to our bridge app
    Logger.info("Binding service \"" + serviceName + "\" to app \"" + DEFAULT_BRIDGEAPP_NAME + "\"")
    proc = Popen(["cf bind-service " + DEFAULT_BRIDGEAPP_NAME + " \"" + serviceName + "\""], 
                 shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if proc.returncode != 0:
        Logger.info("Unable to bind service to the bridge app, error was: " + out)
        return None

    return DEFAULT_BRIDGEAPP_NAME

# find given bound app, and look for the passed bound service in cf.  once
# found in VCAP_SERVICES, look for the credentials setting, and extract
# userid, password.  Raises Exception on errors
def getGlobalizationCredentialsFromBoundApp (service=GLOBALIZATION_SERVICE, binding_app=None):
    # if no binding app parm passed, go looking to find a bound app for this one
    if binding_app == None:
        binding_app = findBoundAppForService(service)
    # if still no binding app, and the user agreed, CREATE IT!
    if binding_app == None:
        setupSpace = os.environ.get('SETUP_SERVICE_SPACE')
        if (setupSpace != None) and (setupSpace.lower() == "true"):
            binding_app = createBoundAppForService(service, GLOBALIZATION_SERVICE_PLAN)
        else:
            raise Exception("Service \"" + service + "\" is not loaded and bound in this space.  " + LABEL_COLOR + "Please add the service to the space and bind it to an app, or set the 'Set up service and space for me' on the job to allow the space to be setup automatically" + LABEL_NO_COLOR)

    # if STILL no binding app, we're out of options, just fail out
    if binding_app == None:
        raise Exception("Unable to access an app bound to the " + service + " - this must be set to get the proper credentials.")

    # try to read the env vars off the bound app in cloud foundry, the one we
    # care about is "VCAP_SERVICES"
    verProc = Popen(["cf env \"" + binding_app + "\""], shell=True, 
                    stdout=PIPE, stderr=PIPE)
    verOut, verErr = verProc.communicate();

    if verProc.returncode != 0:
        raise Exception("Unable to read credential information off the app bound to " + service + " - please check that it is set correctly.")

    envList = []
    envIndex = 0
    inSection = False
    # the cf env var data comes back in the form
    # blah blah blah
    # {
    #    <some json data for a var>
    # }
    # ... repeat, possibly including blah blah blah
    #
    # parse through it, and extract out just the json blocks
    for line in verOut.splitlines():
        if inSection:
            envList[envIndex] += line
            if line.startswith("}"):
                # block end
                inSection = False
                envIndex = envIndex+1
        elif line.startswith("{"): 
            # starting a block
            envList.append(line)
            inSection = True
        else:
            # just ignore this line
            pass

    # now parse that collected json data to get the actual vars
    jsonEnvList = {}
    for x in envList:
        jsonEnvList.update(json.loads(x))

    api_key = ""
    uri = ""

    # find the credentials for the service in question
    if jsonEnvList != None:
        serviceList = jsonEnvList['VCAP_SERVICES']
        if serviceList != None:
            analyzerService = serviceList[service]
            if analyzerService != None:
                credentials = analyzerService[0]['credentials']
                uri = credentials['uri']
                api_key = credentials['api_key']

    if not (api_key) or not (uri):
        raise Exception("Unable to get bound credentials for access to the Static Analysis service.")

    return api_key, uri

def setenvvariable(key, value, filename="setenv_globalization.sh"):
    keyvalue = 'export %s=%s\n' % (key, value)
    open(filename, 'a+').write(keyvalue)

# begin main execution sequence

try:
    Logger = setupLogging()
    parsedArgs = parseArgs()
    Logger.info("Getting credentials for Globalization service")
    api_key, uri = getGlobalizationCredentialsFromBoundApp()
    dashboard = findServiceDashboard(GLOBALIZATION_SERVICE)
    Logger.info("Target uri for Globalization Service is " + uri)
    Logger.info("Writing credentials to setenv_globalization.sh")
    setenvvariable('GAAS_API_KEY', api_key)
    setenvvariable('GAAS_ENDPOINT', uri)
    setenvvariable('GAAS_DASHBOARD', dashboard)

    # allow testing connection without full job scan and submission
    if parsedArgs['loginonly']:
        Logger.info("LoginOnly set, login complete, exiting")
        sys.exit(0)

except Exception, e:
    Logger.warning("Exception received", exc_info=e)
    sys.exit(1)

