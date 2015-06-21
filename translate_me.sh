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
    echo "Usage: `basename $0` -s source_pattern -p project_name [-r CREATE|UPDATE] [-d] [-h]"
    echo ""
    echo "Using IBM Globalization Service on Bluemix this script translates files that match source_pattern" 
    echo ""
    echo "-s        Name of the Source file for translation.  Will look for this filename, if not found will search the directory tree for the file"
    echo "-p        Name of the Globalization project to create"
    echo "-r        [default=create] stage to run.  create or update.  If create a project will be created if needed and strings will be downloaded, if update then manually translated strings will be updated in the Globalization Service"
    echo "-d        Debug mode"
    echo "-h        Displays this usage information"
    echo ""
}

debugme() {
  [[ $DEBUG = 1 ]] && "$@" || :
}

print_limitations() {
    echo -e "${label_color}Current limitations and assumptions:${no_color}"
    echo "  - source pattern will look for files of the format [prefix]_[lang].[type].  For example whateveriwant_en.properties, something_fr.json"
    echo "  - desire all languages translated"
    echo "  - translated files will be placed in the same directory as the source file"
}

wait_for_translation(){
    local project_id=$1
    if [ -z $project_id ]; then 
        echo -e "${red}No project id passed in ${no_color}"
        return 1
    fi 
    local COUNTER=0
    TRANSLATION_STATE="in progress"
    while [[ ( $COUNTER -lt 180 ) && ("${TRANSLATION_STATE}" == "in progress") ]]; do
        let COUNTER=COUNTER+1
        status=$(java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd project-info -p ${project_id} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY})
        # strip off junk 
        status=${status%*]*}
        debugme echo "${status}"
        status=${status#*translationStatusByLanguage*}
        debugme echo "${status}"
        status=${status#=[*}
        debugme echo "${status}"
        echo ${status} | grep "IN_PROGRESS"
        STILL_WORKING=$?
        if [ $STILL_WORKING -ne 0 ]; then 
            TRANSLATION_STATE="completed"
        else 
            sleep 15
        fi  
        echo "Translation is ${TRANSLATION_STATE}: ${status}"
        echo ""
    done

    if [ "${TRANSLATION_STATE}" == "completed" ]; then 
        return 0
    else
        return 1
    fi 
}

update_project_with_translated_files(){
    echo "update_project_with_translated_files"
    #########################################################
    # Find and update all files that match input pattern    #
    #########################################################
    # check if this is a full path 
    if [ -f ${INPUT_PATTERN} ]; then 
        echo "found individual file ${INPUT_PATTERN}"
        export source_files="$INPUT_PATTERN"
    else 
        echo "searching directory structure for ${INPUT_PATTERN}"
        export source_files=$(find `pwd` -name ${INPUT_PATTERN})
        echo "${source_files}"
        if [ -z "${source_files}" ]; then 
            echo -e "${red}Could not locate source file that matches ${INPUT_PATTERN} ${no_color}"
            echo "Directory structure:"
            find . 
            return 1
        fi 
    fi 

    for file in $source_files; do
        cur_dir=`pwd`
        local_file_path="${file##${cur_dir}/}"
        echo ""
        echo ""
        echo "Processing $local_file_path"
        directory="${file%/*}"
        if [ "${directory}" == "${file}" ]; then 
            directory="."
        fi 
        debugme echo "directory of resources:$directory"
        filename="${file##/*/}"
        debugme echo "source filename:$filename" 
        extension="${filename##*.}"
        debugme echo "filetype:$extension"
        case $extension in
            'properties') filetype="java";;
            'json') filetype="json";;
            ?) 
            echo -e "${red}Unrecognized file type $extension used";
            return 1
        esac

        # find the naming pattern  
        prefix="${filename%%_*}"
        if [ -z "$prefix" ]; then
            echo -e "${red}Non supported input.  Assuming the input is of type [prefix]_[lang].[type] ${no_color}"
            return 1 
        fi 
        debugme echo "prefix:${prefix}"
        source_lang="${filename#*_}"
        source_lang="${source_lang%%.*}"
        echo "source language:${source_lang}"

        # Often translation centers send back non slightly different extensions than what the Globalization Service expects
        if [ "${source_lang}" == "zh_Hans" ]; then 
            source_lang="zh-Hans"
        elif [ "${source_lang}" == "zh_Hant" ]; then 
            source_lang="zh-Hant"
        elif [ "${source_lang}" == "pt_BR" ]; then 
            source_lang="pt-BR"
        fi 
        
        archive_path="${directory##${cur_dir}/}"
        # massage archive path to provide a good project name 
        # remove src if it is there 
        debugme echo "processing package name: $archive_path"
        mypackage=${archive_path##src}
        debugme echo "  removed src: $mypackage"
        # replace / with . 
        mypackage=${mypackage////.} 
        debugme echo "  replaced / with . : $mypackage"
        # removing leading . 
        mypackage=${mypackage##.}
        debugme echo "done processing ${mypackage}"
        if [ -z "${THIS_SUBMISSION_NAME}" ]; then 
            if [ -z ${mypackage} ]; then 
                debugme echo "could not create package name from $archive_path using ${mypackage}"
                if [ -z ${SUBMISSION_NAME} ]; then 
                    echo -e "${red}No submission prefix, no package discovered, using DefaultProject${no_color}"
                    THIS_SUBMISSION_NAME="DefaultProject"
                else 
                    debugme echo "Submission prefix set"
                    THIS_SUBMISSION_NAME="${SUBMISSION_NAME}"
                fi 
            else 
                if [ -z ${SUBMISSION_NAME} ]; then 
                    debugme echo "No submission prefix, using package: ${mypackage}"
                    THIS_SUBMISSION_NAME="${mypackage}"
                else 
                    debugme echo "Submission prefix set, using project: ${SUBMISSION_NAME}.${mypackage}"
                    THIS_SUBMISSION_NAME="${SUBMISSION_NAME}.${mypackage}"
                fi 
            fi 
        fi 
        debugme echo "Creating project ${THIS_SUBMISSION_NAME}"
        
        
        pushd . 
        cd ${directory}

        # upload translated file 
        echo "Uploading ${directory}/${filename}"
        java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd import -f ${file} -l ${source_lang} -t ${filetype} -p ${THIS_SUBMISSION_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY}
        local result=$?
        if [ ${result} -ne 0 ]; then 
            echo "" 
            echo ""
            echo -e "${label_color}Could not process ${directory}/${filename} ${no_color}"
            echo "" 
            echo ""
        else 
            echo -e "${green}Successfully processed ${local_file_path} ${no_color}"
        fi 

        # wait for translation to complete 
        wait_for_translation ${THIS_SUBMISSION_NAME}  

        popd
    done 
    return 0
}

create_project_download_files(){
    ############################################################
    # Find and translate all files that match input pattern    #
    ############################################################
    # check if this is a full path 
    if [ -f ${INPUT_PATTERN} ]; then 
        echo "found individual file ${INPUT_PATTERN}"
        export source_files="$INPUT_PATTERN"
    else 
        echo "searching directory structure for ${INPUT_PATTERN}"
        export source_files=$(find `pwd` -name ${INPUT_PATTERN})
        echo "${source_files}"
        if [ -z "${source_files}" ]; then 
            echo -e "${red}Could not locate source file that matches ${INPUT_PATTERN} ${no_color}"
            echo -e "Please update ${label_color}'Source file name'${no_color} parameter on the job to identify the source property files"
            echo "${label_color}Suggested source files${no_color}"
            find . | grep *en*properties
            find . | grep *en*json
            echo "Directory contents:"
            find . 
            return 1
        fi 
    fi 

    for file in $source_files; do
        cur_dir=`pwd`
        local_file_path="${file##${cur_dir}/}"
        echo ""
        echo ""
        echo "Processing $local_file_path"
        directory="${file%/*}"
        if [ "${directory}" == "${file}" ]; then 
            directory="."
        fi 
        debugme echo "directory of resources:$directory"
        filename="${file##/*/}"
        debugme echo "source filename:$filename" 
        extension="${filename##*.}"
        debugme echo "filetype:$extension"
        case $extension in
            'properties') filetype="java";;
            'json') filetype="json";;
            ?) 
            echo -e "${red}Unrecognized file type $extension used";
            return 1
        esac

        # find the naming pattern  
        prefix="${filename%_*}"
        if [ -z "$prefix" ]; then
            echo -e "${red}Non supported input.  Assuming the input is of type [prefix]_[lang].[type] ${no_color}"
            return 1 
        fi 
        debugme echo "prefix:${prefix}"
        source_lang="${filename#*_}"
        source_lang="${source_lang%%.*}"
        if [ "${source_lang}" != "en" ]; then 
            echo -e "${red}Currently only supports english as source language and not ${source_lang}${no_color}"
            return 2
        fi 
        debugme echo "source language:${source_lang}"
        debugme echo "${label_color}Processed files will be placed in ${directory} and will follow naming pattern:${prefix}_[lang].${extension} ${no_color}"
        
        archive_path="${directory##${cur_dir}/}"
        # massage archive path to provide a good project name 
        # remove src if it is there 
        debugme echo "processing package name: $archive_path"
        mypackage=${archive_path##src}
        debugme echo "  removed src: $mypackage"
        # replace / with . 
        mypackage=${mypackage////.} 
        debugme echo "  replaced / with . : $mypackage"
        mypackage=${mypackage##.}

        debugme echo "done processing ${mypackage}"

        if [ -z "${THIS_SUBMISSION_NAME}" ]; then 
            if [ -z ${mypackage} ]; then 
                debugme echo "could not create package name from $archive_path"
                if [ -z ${SUBMISSION_NAME} ]; then 
                    echo -e "${red}No submission prefix, no package discovered, using DefaultProject${no_color}"
                    THIS_SUBMISSION_NAME="DefaultProject"
                else 
                    debugme echo "Submission prefix set"
                    THIS_SUBMISSION_NAME="${SUBMISSION_NAME}"
                fi 
            else 
                if [ -z ${SUBMISSION_NAME} ]; then 
                    debugme echo "No submission prefix, using package: ${mypackage}"
                    THIS_SUBMISSION_NAME="${mypackage}"
                else 
                    debugme echo "Submission prefix set, using project: ${SUBMISSION_NAME}.${mypackage}"
                    THIS_SUBMISSION_NAME="${SUBMISSION_NAME}.${mypackage}"
                fi 
            fi 
        fi 
        debugme echo "Creating project ${THIS_SUBMISSION_NAME}"

        echo "---------------------------------------------------------------------------------------"
        echo "Checking/creating Globalization Project ${THIS_SUBMISSION_NAME} "
        echo "---------------------------------------------------------------------------------------"
        echo "Creating/checking for IBM Globalization Service project ${THIS_SUBMISSION_NAME}"
        java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd create -p ${THIS_SUBMISSION_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY} -s ${source_lang} -l ${lang_all}
        RESULT=$?
        if [ $RESULT -eq 1 ]; then
            echo "..Project has been already created"
        else 
            echo "..Created project"
        fi  
        
        pushd . 
        cd ${directory}

        # upload source 
        echo "Uploading ${GAAS_SOURCE_FILE}"
        java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd import -f ${file} -l ${source_lang} -t ${filetype} -p ${THIS_SUBMISSION_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY}

        # wait for translation to complete 
        wait_for_translation ${THIS_SUBMISSION_NAME}  

        # download translated files 
        array=(${lang_all//,/ })

        for i in "${!array[@]}"
        do
            OUTPUT_FILE_NAME="${prefix}_${array[i]}.${extension}"
            echo "Downloading ${array[i]} translated file ${OUTPUT_FILE_NAME} into ${archive_path}"
            java -cp "$GAAS_LIB/*" com.ibm.gaas.client.tools.cli.GaasCmd export -f ${OUTPUT_FILE_NAME} -l ${array[i]} -t ${filetype} -p ${THIS_SUBMISSION_NAME} -u ${GAAS_ENDPOINT} -k ${GAAS_API_KEY}
            RESULT=$? 
            if [ $RESULT -ne 0 ]; then
                echo "Failed"
                exit $RESULT
            fi 
            echo ""
        done
        if [ "${extension}" == "properties" ]; then 
            echo "Creating file variations that are typically used with java" 
            cp "${prefix}_zh-Hans.${extension}" "${prefix}_zh_Hans.${extension}"
            cp "${prefix}_zh-Hans.${extension}" "${prefix}_zh-CN.${extension}"
            cp "${prefix}_zh-Hans.${extension}" "${prefix}_zh_CN.${extension}"

            cp "${prefix}_zh-Hant.${extension}" "${prefix}_zh_Hant.${extension}"
            cp "${prefix}_zh-Hant.${extension}" "${prefix}_zh-TW.${extension}"
            cp "${prefix}_zh-Hant.${extension}" "${prefix}_zh_TW.${extension}"

            cp "${prefix}_pt-BR.${extension}" "${prefix}_pt_BR.${extension}"
        else 
            debugme "extension type is ${extension} no need to convert to common file formats for Java."
        fi 

        echo -e "${green}Successfully processed source file ${local_file_path} ${no_color}"
        popd
    done 
    return 0
}

########################
# Process arguments    #
########################
while getopts "s:p:r:hd" OPTION
do
    case $OPTION in
        s) export INPUT_PATTERN=$OPTARG; echo "set INPUT_PATTERN to ${OPTARG}";;
        p) export SUBMISSION_NAME=$OPTARG; echo "set SUBMISSION_NAME to ${OPTARG}";;
        r) export JOB_TYPE=$OPTARG; echo "set JOB_TYPE to ${OPTARG}";;
        h) usage; exit 1;;
        d) usage; export DEBUG=1;;
        ?) 
        usage;
        echo "ERROR: Unrecognized option specified.";
        exit 1
    esac
done
shift `expr $OPTIND - 1`
print_limitations

###################
# Check inputs    #
###################
if [ -z $JOB_TYPE ]; then 
    export JOB_TYPE="CREATE"    
fi 

if [ -z $GAAS_ENDPOINT ]; then 
    export GAAS_ENDPOINT="https://gaas.mybluemix.net/translate"
fi 
if [ -z $GAAS_API_KEY ]; then 
    echo -e "${red}API Key for Globalization Service must be set in the environment${no_color}"
    exit 1
fi 

if [ -z $SUBMISSION_NAME ]; then 
    echo -e "${yellow}No project prefix set${no_color}"
fi 

if [ -z $GAAS_LIB ]; then 
    lib_guess=$(find `pwd` -name gaas-java-client-tools*)
    lib_directory="${lib_guess%/*}"
    if [ -d "${lib_directory}" ]; then 
        export GAAS_LIB="${lib_directory}" 
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


if [ "${JOB_TYPE}" == "UPDATE" ]; then 
    echo "----------------------------------------------------"
    echo "Updating Globalization project with translated files"
    echo "----------------------------------------------------"

   update_project_with_translated_files
   result=$?
   if [ $result -ne 0 ]; then
        echo -e "${red}Failed to Globalize project${no_color}"
        exit $result
   fi 

elif [ "${JOB_TYPE}" == "CREATE" ]; then
    echo "-----------------------------------------------------------------------------------------"
    echo "Checking/creating Globalization project and uploading new strings for machine translation"
    echo "-----------------------------------------------------------------------------------------"
    create_project_download_files
    result=$?
    if [ $result -ne 0 ]; then
        echo -e "${red}Failed to Globalize project${no_color}"
        exit $result
   fi 
else 
    echo "Job type must be either CREATE or UPDATE"
    usage 
    exit 1
fi 


# attempt to find dashboard
export GAAS_DASHBOARD=$(cf service "IBM Globalization" | grep Dashboard | awk '{print $2}')
debugme cf services
debugme cf service "IBM Globalization"
if [ -z "$GAAS_DASHBOARD" ]; then 
    cf services
    cf service "IBM Globalization"
    echo "Using latest cf CLI"
    export GAAS_DASHBOARD=$(${EXT_DIR}/bin/cf service "IBM Globalization" | grep Dashboard | awk '{print $2}')
    debugme ${EXT_DIR}/bin/cf services
    debugme ${EXT_DIR}/bin/cf service "IBM Globalization"

    if [ -z "$GAAS_DASHBOARD" ]; then 
        echo -e "${red}Could not locate dashboard for service IBM Globalization${no_color}"
        export GAAS_DASHBOARD="unknown, please locate the service in your IBM Bluemix dashboard"
    fi 
else
    debugme echo "found GAAS_DASHBOARD :${GAAS_DASHBOARD}"
fi 

if [ $result -eq 0 ]; then
    echo -e "${label_color}All source files have been placed in the archive of this build, and can be used by additional stages${no_color}"
    echo -e "${label_color}All translated files have been put in the same directory as the original source files${no_color}"
    echo 
    echo -e "A typical continuous delivery scenario uses machine translation as a part of their continuous integration process.  Periodically, the translated messages can be reviewed and updated by translation experts.  This is best done directly within the Globalization Service Dashboard on IBM Bluemix.  Manually applied updates to translated strings will note be overwritten by future build processes unless the source string has also changed."  
else 
    echo -e "There are a number of ways that you can get help:"
    echo -e "1. Post a question on ${label_color} https://developer.ibm.com/answers/ ${no_color} and 'Ask a question' with tags 'docker', 'containers' and 'devops-services'"
    echo -e "2. Open a Work Item in our public devops project: ${label_color} https://hub.jazz.net/project/alchemy/Alchemy-Ostanes ${no_color}"
    echo 
    echo -e "You can also review and fork our sample scripts on ${label_color} https://github.com/Osthanes ${no_color}"
fi 
echo 
echo -e "The Globalization Dashboard for this organization and space is located at ${green} ${GAAS_DASHBOARD} ${no_color}"
