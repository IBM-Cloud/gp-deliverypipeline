# Globalization Pipeline for Delivery Pipeline

The IBM Bluemix Globalization Pipeline service allows you to rapidly and dynamically translate your mobile and cloud applications without having to rebuild, redeploy, or disrupt the delivery of your application. This extension lets you use the Globalization Pipeline service in your Delivery Pipeline

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

# license

Apache 2.0, see [LICENSE](LICENSE)
