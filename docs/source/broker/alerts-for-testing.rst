Alerts for Testing
===================

Instructions for accessing and working with alerts for testing purposes.

- `Download Alerts`_
- `Load alerts and test`_

Download Alerts
---------------

Setup
~~~~~

Activate your conda environment.
Then use the following code to create a directory for the alerts and set a persistent environment variable pointing to it.

.. code:: bash

    # set this to the directory path where you want alerts to be stored
    # if it doesn't exist, it will be created
    ALERT_DIR="<path/to/alerts/for/testing/directory>"

    # create persistent environment variables
    echo "export ALERT_DIR='${ALERT_DIR}'" >> "${CONDA_PREFIX}/etc/conda/activate.d/env_vars.sh"
    echo 'unset ALERT_DIR' >> "${CONDA_PREFIX}/etc/conda/deactivate.d/env_vars.sh"

    # create the directory
    mkdir -p "${ALERT_DIR}"

Download ZTF Alerts
~~~~~~~~~~~~~~~~~~~

First, create a directory and persistent environment variable:

.. code:: bash

    # add environment variables
    ALERT_DIR_ZTF="${ALERT_DIR}/ZTF"
    echo "export ALERT_DIR_ZTF='${ALERT_DIR_ZTF}'" >> "${CONDA_PREFIX}/etc/conda/activate.d/env_vars.sh"
    echo 'unset ALERT_DIR_ZTF' >> "${CONDA_PREFIX}/etc/conda/deactivate.d/env_vars.sh"

    # create the directory
    mkdir -p "${ALERT_DIR_ZTF}"

Now download the set of test alerts:

.. code:: bash

    gsutil -m cp "gs://${GOOGLE_CLOUD_PROJECT}-ztf-test_alerts/*" "${ALERT_DIR_ZTF}"

Download ELAsTiCC Alerts
~~~~~~~~~~~~~~~~~~~~~~~~

First, create a directory and persistent environment variable:

.. code:: bash

    # add environment variables
    ALERT_DIR_ELASTICC="${ALERT_DIR}/ELASTICC"
    echo "export ALERT_DIR_ELASTICC='${ALERT_DIR_ELASTICC}'" >> "${CONDA_PREFIX}/etc/conda/activate.d/env_vars.sh"
    echo 'unset ALERT_DIR_ELASTICC' >> "${CONDA_PREFIX}/etc/conda/deactivate.d/env_vars.sh"

    # create the directory
    mkdir -p "${ALERT_DIR_ELASTICC}"

Now download the set of test alerts:

.. code:: bash

    cd "${ALERT_DIR_ELASTICC}"
    tarball_name="LSST_ALERTS_BATCH"

    # download the tarball
    curl -O "https://raw.githubusercontent.com/LSSTDESC/plasticc_alerts/main/tests/test01/${tarball_name}.tar.gz"

    # untar the batch
    tar -xvf LSST_ALERTS_BATCH.tar.gz
    tmp_alert_dir="${tarball_name}/ALERTS"
    cd "${tmp_alert_dir}"

    # untar and unzip all files
    for file in $(ls -1); do
        tar -xvf $file
    done
    for file in $(ls -1 */*.gz); do
        gzip -d $file
    done

    # move alerts to ALERT_DIR_ELASTICC and delete all tarballs
    mv * "${ALERT_DIR_ELASTICC}/."
    cd "${ALERT_DIR_ELASTICC}"
    rm *.tar.gz
    rm -r ${tarball_name}

Load alerts and test
--------------------

Setup
~~~~~~~~~~~~~~~~

Import some modules:

.. code:: python

    from broker_utils import data_utils, gcp_utils
    from broker_utils.schema_maps import load_schema_map
    from broker_utils.tests import TestAlert, TestValidator, local_alerts

Set the keywords that were used to setup your broker instance:

.. code:: python

    # choose one:
    SURVEY = "ztf"
    SURVEY = "elasticc"

    # fill this in:
    TESTID = ""

Load paths to alerts stored locally:

.. code:: python

   # get a generator that returns paths to individual avro files
   paths = local_alerts(SURVEY)
   # note that a generator will only iterate over elements once.
   # if you iterate through all of them or just want the complete set of local alerts,
   # load a new generator.

   # get the path to a single file
   path = next(paths)

Load a schema map:

.. code:: python

    # this fetches it from a "generic" broker bucket that has public access rights
   schema_map = load_schema_map('generic', False, SURVEY)

Setup to publish to a topic:

.. code:: python

   # fill in the name stub for the topic that you'll publish to
   topic_name_stub = ""
   # set the full topic name
   topic = f"{SURVEY}-{topic_name_stub}-{TESTID}"

   # to generate mock results for a pipeline module, add its name to the mock list.
   # the mock results will be attached to the message that you'll publish.
   # if you don't need this, or don't know what it is, just set `mock = None`.
   mock = None
   # mock = ["SuperNNova"]

   # set this verbatim (it will be either json or Avro)
   publish_as = TestAlert.guess_publish_format(topic)

Setup to pull from a subscription:

.. code:: python

    # fill in your subscription name
    subscrip = ""
    # or use
    sub_name_stub = ""
    subscrip = f"{SURVEY}-{sub_name_stub}-{TESTID}"

    # if you plan to do a test that involves pulling a message from a
    # subscription in order to validate the output,
    # then it is recommended that you first purge the subscription.
    # this will delete all messages in the subscription so that you can
    # be sure that any message you pull was created by your test.
    gcp_utils.purge_subscription(subscrip)


Load an alert as a dictionary for local testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Load one of test alerts into a dictionary.
This will allow you to test your code locally using real data.

.. code-block:: python

   # load the alert as a dictionary, dropping the cutouts
   alert_dict = data_utils.load_alert(
       path, 'dict', schema_map=schema_map, drop_cutouts=True
   )

Publish a single alert, then pull from a subscription and check the message
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   # load a TestAlert and use it to publish a message
   test_alert = TestAlert(path, schema_map)
   gcp_utils.publish_pubsub(
       topic,
       message=test_alert.create_msg_payload(publish_as=publish_as, mock=mock),
       attrs=test_alert.create_msg_attrs(),
   )

   # note that the alert_dict that was loaded in the previous section
   # can also be retrieved with:
   alert_dict = test_alert.data["dict"]

   # pull a message and unpack the payload as a dict
   msg = gcp_utils.pull_pubsub(subscrip, max_messages=1)  # this returns a list
   msg_dict = data_utils.decode_alert(msg[0], return_as="dict")

   # look at the message to see if it is as-expected
   msg_dict

Publish a batch of alerts, then pull from a subscription and validate the message ids
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Publish:

.. code-block:: python

   # create a publisher client now to avoid instantiating a new one for every alert
   from google.cloud import pubsub_v1
   publisher = pubsub_v1.PublisherClient()

   # publish a batch of test alerts
   # keep a list of ids for later comparison
   published_alert_ids = []
   i_max = 100  # for sanity, limit the max number of alerts published

   for i, path in enumerate(local_alerts(SURVEY)):
       test_alert = TestAlert(path, schema_map)

       gcp_utils.publish_pubsub(
           topic,
           message=test_alert.create_msg_payload(publish_as=publish_as, mock=mock),
           attrs=test_alert.create_msg_attrs(),
           publisher=publisher
       )

       published_alert_ids.append(test_alert.ids)
       if i > i_max:
           break

Wait to give the alerts time to make their way through the pipeline.
About 10 seconds per module should be plenty.
Then pull and validate:

.. code:: python

   # pull messages from the subscription and compare the ids with the published alerts
   validator = TestValidator(subscrip, published_alert_ids, schema_map)
   success, pulled_msg_ids = validator.pull_and_compare_ids()

If everything worked as expected, the validator will report ``success = True``.
