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

_ME=$0

_id() {
    _LINENO=$1
    shift
    echo >&2 "${_ME}:${_LINENO}:" "$*"
}

_id $LINENO

if [ ! -d ./test -o ! -f ./translate_me.sh ];
then
    echo "Error - run this from the top level  (peer to translate_me.sh )" >&2
    _id $LINENO
    exit 1
fi

if [ "x${GP_FAKE_BROKER}" = "x" ];
then
    echo "Error - GP_FAKE_BROKER needs to be set. See the README.md"
    _id $LINENO
    exit 1
fi

_id $LINENO
# clean up
rm -vfr ./test/test_es.properties ./test/test_[a-df-z]*  ./test/tmp || true
rm -vfr ./test/test2* || true
mkdir -v ./test/tmp
export EXT_DIR=./test/tmp

# compare JSON, normalized
cmp_json() {
    ACTUAL=$1
    EXPECT=$2
    python -mjson.tool < $ACTUAL > ${EXT_DIR}/actual.json || exit 1
    python -mjson.tool < $EXPECT > ${EXT_DIR}/expect.json || exit 1
    diff -w ${EXT_DIR}/expect.json ${EXT_DIR}/actual.json
}



_id $LINENO
# verify we can LIST
bash ./translate_me.sh -r CREATE -t LIST -s test_en.properties | tee ${EXT_DIR}/all.txt

EXPECT_ALL='Available target languages: de,es,fr,it,ja,ko,pt-BR,zh-Hans,zh-Hant'

if ! fgrep -q "${EXPECT_ALL}" ${EXT_DIR}/all.txt;
then
    echo 'Error, available list does not match expected:' >&2
    echo ${EXPECT_ALL} >&2
    _id $LINENO
    exit 1
else
    _id $LINENO
    echo 'OK: Available list OK.'
fi

# verify that on failure, we get out
if bash ./translate_me.sh -s testbad_en.json -p testbad -r CREATE -t qru;
then
    echo 'FAIL: Hey, testbad_en.json isn’t valid JSON, script should have failed!' >&2
    _id $LINENO
    exit 1
else
    _id $LINENO
    echo 'OK: correct failure on bad JSON' >&2
fi

# test with pseudo 
bash ./translate_me.sh  -s test_en.properties -p test -r CREATE -t qru || ( echo 'Failed' >&2 ; exit 1 )

# verify file was translated
if [ ! -f ./test/test_qru.properties ];
then
    echo 'Error, target ./test/test_qru.properties was not created' >&2
    _id $LINENO
    exit 1
fi

# cyrillic transliteration (partial)
if ! fgrep -q 'hello=\u0425\u0435\u043B\u043B\u043E' ./test/test_qru.properties;
then
    echo 'Error, pseudotranslated content not as expected' >&2
    _id $LINENO
    exit 1
fi

_id $LINENO
# test basic conversio of all
bash ./translate_me.sh  -s test_en.properties -p testall -r CREATE -t ALL || ( echo 'Failed to translate all' >&2 ; exit 1 ) || exit 1

# verify files/line counts
( wc -l $(ls test/test_* | env LC_COLLATE=C sort)  | tr -s ' ' ' ' |  env LC_COLLATE=C sort -n | tee test/ACTUAL | diff -w test/expect-wc-all.txt  - ) || (echo 'step ALL failed' >&2 ;  echo '-' ; cat test/ACTUAL ; echo '-' ; exit 1 ) || exit 1

# if OK, no need to keep this
rm test/ACTUAL

_id $LINENO
# test JSON
cp ./test/0-test2_en.json ./test/test2_en.json
rm -fv ./test/test2_qru.json ./test/test2_ko.json ./test/test2_de.json
bash ./translate_me.sh -s test2_en.json -p test2 -r CREATE -t qru,ko || ( echo 'Failed' >&2 ; exit 1 ) || exit 1

if ! cmp_json ./test/test2_qru.json test/0-expect-test2_qru.json;
then
    echo 'Error: target test/test2_qru.json did not match #1' >&2
    _id $LINENO
    exit 1
fi

if [ ! -f ./test/test2_ko.json ];
then
    echo 'Error: test/test2_ko.json did not exist' >&2
    _id $LINENO
    exit 1
fi

if [ -f ./test/test2_de.json ];
then
    echo 'Error: test/test2_de.json DID exist and it should not have' >&2
    _id $LINENO
    exit 1
fi


_id $LINENO
# cleanup
rm -fv ./test/test2_qru.json ./test/test2_ko.json ./test/test2_de.json
# test JSON again with an update
cp ./test/1-test2_en.json ./test/test2_en.json
bash ./translate_me.sh -s test2_en.json -p test2 -r CREATE -t qru,de || ( echo 'Failed' >&2 ; exit 1 ) | exit 1

if ! cmp_json ./test/test2_qru.json test/1-expect-test2_qru.json;
then
    echo 'Error: target test/test2_qru.json did not match #2' >&2
    _id $LINENO
    exit 1
fi

if [ ! -f ./test/test2_de.json ];
then
    echo 'Error: test/test2_de.json did not exist (it was an added target lang)' >&2
    _id $LINENO
    exit 1
fi

if [ -f ./test/test2_ko.json ];
then
    echo 'Error: test/test2_ko.json DID exist and it should not have (it was a removed target lang)' >&2
    _id $LINENO
    exit 1
fi

_id $LINENO
echo 'All tests OK!'
exit 0
