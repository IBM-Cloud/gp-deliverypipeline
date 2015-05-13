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

usage()
{
    echo "Usage: `basename $0` [-s source_pattern] [-o output_directory]"
    echo ""
    echo "Using IBM Globalization Service on Bluemix translates files that match source_pattern" 
    echo ""
    echo "-s        Source file for translation."
    echo "-d        Output directory for translated files.  Defaults to the location of the source pattern."
    echo "-h        Displays this usage information"
    echo ""
}

print_limitations() {
    echo -e "${label_color}Current limitations and assumptions:${no_color}"
    echo "  - source file is english"
    echo "  - desire all languages translated"
    echo "  - translated files will be placed in the same directory as the source file"
}

while getopts "sdh" OPTION
do
    case $OPTION in
        s) GAAS_SOURCE_FILE=$OPTARG;;
        o) DEBUG=true;;
        h) usage; exit 1;;
        ?) 
        usage;
        echo "ERROR: Unrecognized option specified.";
        exit 1
    esac
done
shift `expr $OPTIND - 1`


if [ -z $GAAS_ENDPOINT ]; then 
    export GAAS_ENDPOINT="https://gaas.mybluemix.net/translate"
fi 
if [ -z $GAAS_API_KEY ]; then 
    echo -e "${red}API Key for Globalization Service must be set in the environment${no_color}"
    exit 1
fi 
if [ -z $SUBMISSION_NAME ]; then 
    echo -e "${red}SUBMISSION_NAME must be set in the environment${no_color}"
    exit 1
fi 
if [ -z $GAAS_LIB ]; then 
    if [ -d "lib" ]; then 
        export GAAS_LIB="lib" 
    else 
        echo -e "${red}GAAS_LIB must be set in the environment${no_color}"
        exit 1
    fi 
fi 
if [ -z $INPUT_PATTERN ]; then 
    echo -e "${red}INPUT_PATTERN is not set${no_color}"
    exit 1
else 
    echo "${INPUT_PATTERN} is the source file pattern"
fi 

source_files=$(find `pwd` -name ${INPUT_PATTERN})
for file in $source_files; do
    echo $file 
    directory="${file%/*}"
    echo "directory of resources:$directory"
    filename="${file##/*/}"
    echo "source filename:$filename" 
    extension="${filename##*.}"
    echo "filetype:$extension"
    # find the naming pattern  
    prefix="${filename%_*}"
    if [ -z "$prefix" ]; then
        echo -e "${red}Non supported input.  Assuming the input is of type [prefix]_[lang].[type] ${no_color}"
        exit 1 
    fi 
    echo "prefix:${prefix}"
    source_lang="${filename##*_}"
    source_lang="${source_lang%%.*}"
    if [ "${source_lang}" != "en" ]; then 
        echo -e "${red}Currently only supports english as source language and not ${source_lang}${no_color}"
        exit 2
    fi 
    echo "source language:${source_lang}"
    echo "naming pattern:${prefix}_[lang].${extension}"
done 
exit 
print_limitations
set -x

# create  project 
java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd create -p ${SUBMISSION_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY} -s en -l ${lang_all}
RESULT=$?
if [ $RESULT -eq 1 ]; then
    echo "Project has been already created"
else 
    echo "Created project"
fi  
# upload source 
echo "uploading ${GAAS_SOURCE_FILE}"
java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd import -f ${GAAS_SOURCE_FILE} -l en -t java -p ${SUBMISSION_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY}
# download translated files 
array=(${lang_all//,/ })
export OUTPUT_PREFIX="Language"
export OUTPUT_TYPE="properties"
for i in "${!array[@]}"
do
    echo "$i=>${array[i]}"
    OUTPUT_FILE_NAME="${OUTPUT_PREFIX}_${array[i]}.${OUTPUT_TYPE}"
    echo "downlaoding ${array[i]} translated files to ${OUTPUT_FILE_NAME}"
    java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd export -f ${OUTPUT_FILE_NAME} -l ${array[i]} -t java -p ${SUBMISSION_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY}
    RESULT=$? 
    if [ $RESULT -ne 0 ]; then
        echo "Failed"
        exit $RESULT
    fi 
done