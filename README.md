# Globalization Pipeline for Delivery Pipeline

The IBM Bluemix 
[Globalization Pipeline](https://github.com/IBM-Bluemix/gp-common#globalization-pipeline)
service allows you to rapidly and dynamically translate your mobile and cloud applications without having to rebuild, redeploy, or disrupt the delivery of your application. This extension lets you use the Globalization Pipeline service in your Delivery Pipeline.

[![Build Status](https://travis-ci.org/IBM-Bluemix/gp-deliverypipeline.svg?branch=master)](https://travis-ci.org/IBM-Bluemix/gp-deliverypipeline)

# documentation 


References 
* [IBM Globalization Pipeline Documentation](https://www.ng.bluemix.net/docs/#services/GlobalizationPipeline/index.html)
* [How to use IBM DevOps Services with Containers](https://developer.ibm.com/bluemix/docs/set-up-continuous-delivery-ibm-containers/)
* [Globalization Pipeline SDKs](https://developer.ibm.com/open/ibm-bluemix-globalization-pipeline-service/)
* [Using dynamic resource bundles in Java](https://github.com/IBM-Bluemix/gp-java-client)
* [Using dynamic resource bundles in Javascript Node](https://github.com/IBM-Bluemix/gp-js-client)

# testing locally

## Mac setup

(needed for `\e` echos)

* `brew install coreutils`
* `export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"`

## Running the tests against the fake broker

* You need to get the setting for `GP_FAKE_BROKER`. Contact [@srl295](https://srl295.github.io) if you have questions.
* Now you can run:

```
env GP_FAKE_BROKER=____________________ python ./test/broker_run.py bash ./test/runtests.sh
```
The test will return zero on success, non-zero on failure.

* Note that tests are run from the top level directory.

## Running the test against a real GP instance

* Set the variables `GAAS_ENDPOINT`, `GAAS_USER_ID`, `GAAS_INSTANCE_ID`, and `GAAS_PASSWORD`
* run:

```
bash ./test/runtests.sh
```

* Note that tests are run from the top level directory.

Community
===
* View or file GitHub [Issues](https://github.com/IBM-Bluemix/gp-deliverypipeline/issues)
* Connect with the open source community on [developerWorks Open](https://developer.ibm.com/open/ibm-bluemix-globalization-pipeline/)

Contributing
===
See [CONTRIBUTING.md](CONTRIBUTING.md).

License
===
Apache 2.0. See [LICENSE](LICENSE)

> Licensed under the Apache License, Version 2.0 (the "License");
> you may not use this file except in compliance with the License.
> You may obtain a copy of the License at
> 
> http://www.apache.org/licenses/LICENSE-2.0
> 
> Unless required by applicable law or agreed to in writing, software
> distributed under the License is distributed on an "AS IS" BASIS,
> WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
> See the License for the specific language governing permissions and
> limitations under the License.