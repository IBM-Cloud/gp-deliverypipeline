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
export no_color='\e[0m' 

################
# Languages    #
################
export lang_en='en'
export lang_all='de,es,fr,it,ja,pt-BR,zh-Hans,zh-Hant'

print_limitations() {
    echo -e "${label_color}Current limitations and assumptions:${no_color}"
    echo "  - source file is english"
    echo "  - desire all languages translated"
    echo "  - translated files will be placed in the same directory as the source file"
}

if [ -z $GAAS_ENDPOINT ]; then 
    export GAAS_ENDPOINT="https://gaas.mybluemix.net/translate"
fi 
if [ -z $GAAS_API_KEY ]; then 
    echo -e "${red}API Key for Globalization Service must be set in the environment${no_color}"
    exit 1
fi 
if [ -z $GAAS_PROJECT_NAME ]; then 
    echo -e "${red}GAAS_PROJECT_NAME must be set in the environment${no_color}"
    exit 1
fi 
if [ -z $1 ]; then 
    echo -e "Expected source file to be passed in as argument"
    exit 1
fi 
export GAAS_SOURCE_FILE=$1
if [ ! -f $GAAS_SOURCE_FILE ]; then 
    echo -e "${red}${GAAS_SOURCE_FILE} does not exist${no_color}"
    exit 1
else 
    echo "${GAAS_SOURCE_FILE} is the source file"
fi 

print_limitations
set -x

# create  project 
java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd create -p ${GAAS_PROJECT_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY} -s en -l ${lang_all}
RESULT=$?
if [ $RESULT -eq 1 ]; then
    echo "Project has been already created"
else 
    echo "Created project"
fi  
# upload source 
echo "uploading ${GAAS_SOURCE_FILE}"
java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd import -f ${GAAS_SOURCE_FILE} -l en -t java -p ${GAAS_PROJECT_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY}
# download translated files 
array=(${lang_all//,/ })
export OUTPUT_PREFIX="Language"
export OUTPUT_TYPE="properties"
for i in "${!array[@]}"
do
    echo "$i=>${array[i]}"
    OUTPUT_FILE_NAME="${OUTPUT_PREFIX}_${array[i]}.${OUTPUT_TYPE}"
    echo "downlaoding ${array[i]} translated files to ${OUTPUT_FILE_NAME}"
    java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd export -f ${OUTPUT_FILE_NAME} -l ${array[i]} -t java -p ${GAAS_PROJECT_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY}
    RESULT=$? 
    if [ $RESULT -ne 0 ]; then
        echo "Failed"
        exit $RESULT
    fi 
done