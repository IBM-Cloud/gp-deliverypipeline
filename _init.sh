#!/bin/bash

#********************************************************************************
# Copyright 2014 IBM
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

#############
# Colors    #
#############
export green='\e[0;32m'
export red='\e[0;31m'
export label_color='\e[0;33m'
export no_color='\e[0m' # No Color

##################################################
# Simple function to only run command if DEBUG=1 # 
### ###############################################
debugme() {
  [[ $DEBUG = 1 ]] && "$@" || :
}

set +e
set +x 
##################################################
# capture packages that on the originial container 
##################################################
if [[ $DEBUG -eq 1 ]]; then
    dpkg -l | grep '^ii' > $EXT_DIR/pkglist
fi 

###############################
# Configure extension PATH    #
###############################
if [ -n $EXT_DIR ]; then 
    export PATH=$EXT_DIR:$PATH
fi 
##############################
# Configure extension LIB    #
##############################
if [ -z $GAAS_LIB ]; then 
    export GAAS_LIB="${EXT_DIR}/lib"
fi 

################################
# Setup archive information    #
################################
if [ -z $WORKSPACE ]; then 
    echo -e "${red}Please set WORKSPACE in the environment${no_color}"
    ${EXT_DIR}/print_help.sh
    exit 1
fi 

if [ -z $ARCHIVE_DIR ]; then 
    echo "${label_color}ARCHIVE_DIR was not set, setting to WORKSPACE/archive ${no_color}"
    export ARCHIVE_DIR="${WORKSPACE}"
fi 

if [ -d $ARCHIVE_DIR ]; then
  echo "Archiving to $ARCHIVE_DIR"
else 
  echo "Creating archive directory $ARCHIVE_DIR"
  mkdir $ARCHIVE_DIR 
fi 
export LOG_DIR=$ARCHIVE_DIR

#############################
# Install Cloud Foundry CLI #
#############################
pushd . 
echo "Installing Cloud Foundry CLI"
cd $EXT_DIR 
mkdir bin
cd bin
curl --silent -o cf-linux-amd64.tgz -v -L https://cli.run.pivotal.io/stable?release=linux64-binary &>/dev/null 
gunzip cf-linux-amd64.tgz &> /dev/null
tar -xvf cf-linux-amd64.tar  &> /dev/null

cf help &> /dev/null
RESULT=$?
if [ $RESULT -ne 0 ]; then
    echo "Cloud Foundry CLI not already installed, adding CF to PATH"
    export PATH=$PATH:$EXT_DIR/bin
else 
    echo 'Cloud Foundry CLI already available in container.  Latest CLI version available in ${EXT_DIR}/bin'  
fi 

# check that we are logged into cloud foundry correctly
cf spaces 
RESULT=$?
if [ $RESULT -ne 0 ]; then
    echo -e "${red}Failed to check cf spaces to confirm login${no_color}"
    exit $RESULT
else 
    echo -e "${green}Successfully logged into IBM Bluemix${no_color}"
fi 
popd 

export container_cf_version=$(cf --version)
export latest_cf_version=$(${EXT_DIR}/bin/cf --version)
echo "Container Cloud Foundry CLI Version: ${container_cf_version}"
echo "Latest Cloud Foundry CLI Version: ${latest_cf_version}"

################################
# get the extensions utilities #
################################
pushd . >/dev/null
cd $EXT_DIR 
git clone https://github.com/Osthanes/utilities.git utilities
popd >/dev/null

###################################
# Configure Globalization Service #
###################################
echo "Setting up space"
pushd . 
cd ${EXT_DIR}
python globalization_check.py 
RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo -e "${red}Failed to setup/check service in space${no_color}"
    exit $RESULT
else 
    echo -e "${green}Successfully setup/checked service within Bluemix space${no_color}"
fi 
debugme cat setenv_globalization
. setenv_globalization.sh
rm setenv_globalization.sh  
popd 

#############################################
# Capture packages installed on the container  
#############################################
if [[ $DEBUG -eq 1 ]]; then
    dpkg -l | grep '^ii' > $EXT_DIR/pkglist2
    diff $EXT_DIR/pkglist $EXT_DIR/pkglist2
fi