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

if [ ! -d ./test -o ! -f ./translate_me.sh ];
then
    echo "Error - run this from the top level  (peer to translate_me.sh )" >&2
    exit 1
fi

if [ "x${GP_FAKE_BROKER}" = "x" ];
then
    echo "Error - GP_FAKE_BROKER needs to be set. See the README.md"
    exit 1
fi

# clean up
rm -vfr ./test/test_es.properties ./test/test_[a-df-z]*  ./test/tmp || true
rm -vfr ./test/test2* || true
mkdir -v ./test/tmp
export EXT_DIR=./test/tmp

# test with pseudo 
bash ./translate_me.sh  -s test_en.properties -p test -r CREATE -t qru || ( echo 'Failed' >&2 ; exit 1 )

# verify file was translated
if [ ! -f ./test/test_qru.properties ];
then
    echo 'Error, target ./test/test_qru.properties was not created' >&2
    exit 1
fi

# cyrillic transliteration (partial)
if ! fgrep -q 'hello=\u0425\u0435\u043B\u043B\u043E' ./test/test_qru.properties;
then
    echo 'Error, pseudotranslated content not as expected' >&2
    exit 1
fi

# test basic conversio of all
bash ./translate_me.sh  -s test_en.properties -p testall -r CREATE -t ALL || ( echo 'Failed to translate all' >&2 ; exit 1 ) || exit 1

# verify files/line counts
( wc -l $(ls test/test_* | env LC_COLLATE=C sort)  | tr -s ' ' ' ' |  env LC_COLLATE=C sort -n | tee test/ACTUAL | diff -w test/expect-wc-all.txt  - ) || (echo 'step ALL failed' >&2 ;  echo '-' ; cat test/ACTUAL ; echo '-' ; exit 1 ) || exit 1

# if OK, no need to keep this
rm test/ACTUAL

# test JSON
cp ./test/0-test2_en.json ./test/test2_en.json
bash ./translate_me.sh -s test2_en.json -p test2 -r CREATE -t qru || ( echo 'Failed' >&2 ; exit 1 ) || exit 1

if ! diff -w ./test/test2_qru.json test/0-expect-test2_qru.json;
then
    echo 'Error: target test/test2_qru.json did not match #1' >&2
    exit 1
fi


# cleanup
# rm -fv ./test/test2_qru.json
# test JSON again with an update
cp ./test/1-test2_en.json ./test/test2_en.json
bash ./translate_me.sh -s test2_en.json -p test2 -r CREATE -t qru || ( echo 'Failed' >&2 ; exit 1 ) | exit 1

if ! diff -w ./test/test2_qru.json test/1-expect-test2_qru.json;
then
    echo 'Error: target test/test2_qru.json did not match #2' >&2
    exit 1
fi

echo 'All tests OK!'
exit 0
