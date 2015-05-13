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

STATIC_ANALYSIS_SERVICE='Static Analyzer'
DEFAULT_SERVICE=STATIC_ANALYSIS_SERVICE
DEFAULT_SERVICE_PLAN="free"
DEFAULT_SERVICE_NAME=DEFAULT_SERVICE
DEFAULT_SCANNAME="staticscan"
DEFAULT_BRIDGEAPP_NAME="containerbridge"

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
def createBoundAppForService (service=DEFAULT_SERVICE):

    if not checkAndCreateBridgeApp():
        return None

    # look to see if we have the service in our space
    serviceName = findServiceNameInSpace(service)

    # if we don't have the service name, means the tile isn't created in our space, so go
    # load it into our space if possible
    if serviceName == None:
        Logger.info("Service \"" + service + "\" is not loaded in this space, attempting to load it")
        serviceName = DEFAULT_SERVICE_NAME
        command = "cf create-service \"" + service + "\" \"" + DEFAULT_SERVICE_PLAN + "\" \"" + serviceName + "\""
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
def getCredentialsFromBoundApp (service=DEFAULT_SERVICE, binding_app=None):
    # if no binding app parm passed, go looking to find a bound app for this one
    if binding_app == None:
        binding_app = findBoundAppForService(service)
    # if still no binding app, and the user agreed, CREATE IT!
    if binding_app == None:
        setupSpace = os.environ.get('SETUP_SERVICE_SPACE')
        if (setupSpace != None) and (setupSpace.lower() == "true"):
            binding_app = createBoundAppForService(service)
        else:
            raise Exception("Service \"" + service + "\" is not loaded and bound in this space.  Please add the service to the space and bind it to an app, or set the parameter to allow the space to be setup automatically")

    # if STILL no binding app, we're out of options, just fail out
    if binding_app == None:
        raise Exception("Unable to access an app bound to the Static Analysis service - this must be set to get the proper credentials.")

    # try to read the env vars off the bound app in cloud foundry, the one we
    # care about is "VCAP_SERVICES"
    verProc = Popen(["cf env \"" + binding_app + "\""], shell=True, 
                    stdout=PIPE, stderr=PIPE)
    verOut, verErr = verProc.communicate();

    if verProc.returncode != 0:
        raise Exception("Unable to read credential information off the app bound to the Static Analysis service - please check that it is set correctly.")

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

    userid = ""
    password = ""

    # find the credentials for the service in question
    if jsonEnvList != None:
        serviceList = jsonEnvList['VCAP_SERVICES']
        if serviceList != None:
            analyzerService = serviceList[service]
            if analyzerService != None:
                credentials = analyzerService[0]['credentials']
                userid = credentials['bindingid']
                password = credentials['password']

    if not (userid) or not (password):
        raise Exception("Unable to get bound credentials for access to the Static Analysis service.")

    return userid, password

# given userid and password, attempt to authenticate to appscan for
# future calls
def appscanLogin (userid, password):
    proc = Popen(["appscan.sh login -u " + userid + " -P " + password + ""], 
                      shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if not "Authenticated successfully." in out:
        raise Exception("Unable to login to Static Analysis service")

# callout to appscan to prepare a current irx file, return a set of
# the files created by the prepare
def appscanPrepare ():

    # sadly, prepare doesn't tell us what file it created, so find
    # out by a list compare before/after
    oldIrxFiles = []
    for file in os.listdir("."):
        if file.endswith(".irx"):
            oldIrxFiles.append(file)

    proc = Popen(["appscan.sh prepare"], 
                 shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if not "IRX file generation successful" in out:
        if os.environ.get('DEBUG'):
            call(["cat $APPSCAN_INSTALL_DIR/logs/client.log | tail -n 10"], shell=True)
        raise Exception("Unable to prepare code for analysis by Static Analysis service: " + 
                        err)

    # what files are there now?
    newIrxFiles = []
    for file in os.listdir("."):
        if file.endswith(".irx"):
            newIrxFiles.append(file)
    # which files are new?
    newIrxFiles = set(newIrxFiles).difference(oldIrxFiles)

    logMessage = "Generated scans as file(s):"
    for file in newIrxFiles:
        logMessage = logMessage + "\n\t" + file

    Logger.info(logMessage)

    return newIrxFiles

# submit a created irx file to appscan for analysis
def appscanSubmit (filelist):
    if filelist==None:
        raise Exception("No files to analyze")

    # check the env for name of the scan, else use default
    if os.environ.get('SUBMISSION_NAME'):
        scanname=os.environ.get('SUBMISSION_NAME')
    else:
        scanname=DEFAULT_SCANNAME

    # if we have an application version, append it to the scanname
    if os.environ.get('APPLICATION_VERSION'):
        scanname = scanname + "-" + os.environ.get('APPLICATION_VERSION')

    scanlist = []
    index = 0
    for filename in filelist:
        submit_scanname = scanname + "-" + str(index)
        proc = Popen(["appscan.sh queue_analysis -f " + filename +
                      " -n " + submit_scanname], 
                          shell=True, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate();

        transf_found = False
        for line in out.splitlines() :
            if "100% transferred" in line:
                # done transferring
                transf_found = True
            elif not transf_found:
                # not done transferring yet
                continue
            elif line:
                # done, if line isn't empty, is an id
                scanlist.append(line)
                Logger.info("Job for file " + filename + " was submitted as scan " + submit_scanname + " and assigned id " + line)
            else:
                # empty line, skip it
                continue

        index = index + 1

    return scanlist


# get appscan list of current jobs
def appscanList ():
    proc = Popen(["appscan.sh list"], 
                      shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    scanlist = []
    for line in out.splitlines() :
        if "No analysis jobs" in line:
            # no jobs, return empty list
            return []
        elif line:
            # done, if line isn't empty, is an id
            scanlist.append(line)
        else:
            # empty line, skip it
            continue

    return scanlist

# translate a job state to a pretty name
def getStateName (state):
    return {
        0 : "Pending",
        1 : "Starting",
        2 : "Running",
        3 : "FinishedRunning",
        4 : "FinishedRunningWithErrors",
        5 : "PendingSupport",
        6 : "Ready",
        7 : "ReadyIncomplete",
        8 : "FailedToScan",
        9 : "ManuallyStopped",
        10 : "None",
        11 : "Initiating",
        12 : "MissingConfiguration",
        13 : "PossibleMissingConfiguration"
    }.get(state, "Unknown")

# given a state, is the job completed
def getStateCompleted (state):
    return {
        0 : False,
        1 : False,
        2 : False,
        3 : True,
        4 : True,
        5 : True,
        6 : True,
        7 : True,
        8 : True,
        9 : True,
        10 : True,
        11 : False,
        12 : True,
        13 : True
    }.get(state, True)

# given a state, was it completed successfully
def getStateSuccessful (state):
    return {
        0 : False,
        1 : False,
        2 : False,
        3 : True,
        4 : False,
        5 : True,
        6 : True,
        7 : False,
        8 : False,
        9 : False,
        10 : False,
        11 : False,
        12 : False,
        13 : False
    }.get(state, False)

# get status of a given job
def appscanStatus (jobid):
    if jobid == None:
        raise Exception("No jobid to check status")

    proc = Popen(["appscan.sh status -i " + str(jobid)], 
                      shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    if "request is invalid" in err:
        raise Exception("Invalid jobid")

    retval = 0
    try:
        retval = int(out)
    except ValueError:
        raise Exception("Invalid jobid")

    return retval

# cancel an appscan job
def appscanCancel (jobid):
    if jobid == None:
        return

    proc = Popen(["appscan.sh cancel -i " + str(jobid)], 
                      shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

# parse a key=value line, return value
def parseKeyEqVal (line):
    if line == None:
        return None

    eqIndex = line.find("=");
    if eqIndex != -1:
        return line[eqIndex+1:]
    else:
        return None

# extended info on a current appscan job.  this comes back in a form
# similar to:
#NLowIssues=0
#ReadStatus=2
#NHighIssues=0
#Name=appscan.zip
#ScanEndTime=2014-11-20T13:56:04.497Z
#Progress=0
#RemainingFreeRescanMinutes=0
#ParentJobId=00000000-0000-0000-0000-000000000000
#EnableMailNotifications=false
#JobStatus=6
#NInfoIssues=0
#JobId=9b344fc7-bc70-e411-b922-005056924f9b
#NIssuesFound=0
#CreatedAt=2014-11-20T13:54:49.597Z
#UserMessage=Scan completed successfully. The report is ready.
#NMediumIssues=0
#Result=1
#
# parse it and return useful parts.  in particular, returns
# NInfo, NLow, NMedium, NHigh, userMessage
def appscanInfo (jobid):
    if jobid == None:
        return

    command = "appscan.sh info -i " + str(jobid)
    proc = Popen([command], shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    Progress = 100
    NInfo = 0
    NLow = 0
    NMed = 0
    NHigh = 0
    jobName = ""
    userMsg = ""
    for line in out.splitlines() :
        if "NLowIssues=" in line:
            # number of low severity issues found in the scan
            tmpstr = parseKeyEqVal(line)
            if tmpstr != None:
                try:
                    NLow = int(tmpstr)
                except ValueError:
                    NLow = 0

        elif "NMediumIssues=" in line:
            # number of medium severity issues found in the scan
            tmpstr = parseKeyEqVal(line)
            if tmpstr != None:
                try:
                    NMed = int(tmpstr)
                except ValueError:
                    NMed = 0

        elif "NHighIssues=" in line:
            # number of medium severity issues found in the scan
            tmpstr = parseKeyEqVal(line)
            if tmpstr != None:
                try:
                    NHigh = int(tmpstr)
                except ValueError:
                    NHigh = 0

        elif "NInfoIssues=" in line:
            # number of medium severity issues found in the scan
            tmpstr = parseKeyEqVal(line)
            if tmpstr != None:
                try:
                    NInfo = int(tmpstr)
                except ValueError:
                    NInfo = 0

        elif "Progress=" in line:
            # number of medium severity issues found in the scan
            tmpstr = parseKeyEqVal(line)
            if tmpstr != None:
                try:
                    Progress = int(tmpstr)
                except ValueError:
                    Progress = 0

        elif "Name=" in line:
            # number of medium severity issues found in the scan
            tmpstr = parseKeyEqVal(line)
            if tmpstr != None:
                jobName = tmpstr

        elif "UserMessage=" in line:
            # number of medium severity issues found in the scan
            tmpstr = parseKeyEqVal(line)
            if tmpstr != None:
                userMsg = tmpstr

    return NInfo, NLow, NMed, NHigh, Progress, jobName, userMsg

# get the result file for a given job
def appscanGetResult (jobid):
    if jobid == None:
        return

    proc = Popen(["appscan.sh get_result -i " + str(jobid)], 
                      shell=True, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate();

    print "Out = " + out
    print "Err = " + err

# wait for a given set of scans to complete and, if successful,
# download the results
def waitforscans (joblist):
    for jobid in joblist:
        try:
            while True:
                state = appscanStatus(jobid)
                Logger.info("Job " + str(jobid) + " in state " + getStateName(state))
                if getStateCompleted(state):
                    info,low,med,high,prog,name,msg = appscanInfo(jobid)
                    if getStateSuccessful(state):
                        Logger.info("Analysis successful (" + name + ")")
                        #print "\tInfo Issues   : " + str(info)
                        #print "\tLow Issues    : " + str(low)
                        #print "\tMedium Issues : " + str(med)
                        #print "\tHigh Issues   : " + str(high)
                        #print "\tOther Message : " + msg
                        #appscanGetResult(jobid)
                        dash = findServiceDashboard(STATIC_ANALYSIS_SERVICE)
                        if dash != None:
                            print LABEL_GREEN + STARS
                            print "Analysis successful for job \"" + name + "\""
                            print "See current state and output at: " + LABEL_COLOR + " " + dash
                            print LABEL_GREEN + STARS + LABEL_NO_COLOR
                    else: 
                        Logger.info("Analysis unsuccessful (" + name + ")")

                    break
                else:
                    time.sleep(10)
        except Exception:
            # bad id, skip it
            pass


# begin main execution sequence

try:
    Logger = setupLogging()
    parsedArgs = parseArgs()
    Logger.info("Getting credentials for Static Analysis service")
    userid, password = getCredentialsFromBoundApp(service=STATIC_ANALYSIS_SERVICE)
    Logger.info("Connecting to Static Analysis service")
    appscanLogin(userid,password)

    # allow testing connection without full job scan and submission
    if parsedArgs['loginonly']:
        Logger.info("LoginOnly set, login complete, exiting")
        sys.exit(0)

    # if checkstate, don't really do a scan, just check state of current outstanding ones
    if parsedArgs['checkstate']:
        joblist = appscanList()
    else:
        Logger.info("Scanning for code submission")
        files_to_submit = appscanPrepare()
        Logger.info("Submitting scans for analysis")
        joblist = appscanSubmit(files_to_submit)
        Logger.info("Waiting for analysis to complete")

    waitforscans(joblist)

    if parsedArgs['cleanup']:
        # cleanup the jobs we launched (since they're complete)
        print "Cleaning up"
        for job in joblist:
            appscanCancel(job)
        # and cleanup the submitted irx files
        for file in files_to_submit:
            if os.path.isfile(file):
                os.remove(file)
            if os.path.isfile(file+".log"):
                os.remove(file+".log")
except Exception, e:
    Logger.warning("Exception received", exc_info=e)
    sys.exit(1)

