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

[Updated for broker_utils v0.2.37]

Setup
~~~~~~~~~~~~~~~~

Activate your conda environment and open a python prompt.

Import tools from broker_utils:

.. code:: python

    from broker_utils.data_utils import decode_alert, load_alert
    from broker_utils.gcp_utils import publish_pubsub, pull_pubsub, purge_subscription
    from broker_utils.schema_maps import load_schema_map
    from broker_utils.testing import AlertPaths, IntegrationTestValidator, TestAlert

Set the keywords that were used to setup your broker instance.
Choose a survey, and fill in your testid.

.. code:: python

    SURVEY = "ztf"
    SURVEY = "elasticc"
    TESTID = ""

To run an integration test you will deploy your module(s), then publish input messages to the trigger topic and pull output messages from a subscription to the modules ouput topic.

Fill in the name of the topic you will publish to and the subscription you will pull from.

.. code:: python

    topic = ""
    topic = f"{SURVEY}-{topic}-{TESTID}"

    subscrip = ""
    subscrip = f"{SURVEY}-{subscrip}-{TESTID}"

You may want to purge all messages from the subscription before running an integration
test so that old messages do not interfere.

.. code:: python

    purge_subscription(subscrip)

Load a schema map, paths to alerts stored locally, and a ``TestAlert``:

.. code:: python

    apaths = AlertPaths(SURVEY)
    schema_map = load_schema_map('generic', False, SURVEY)

    talert = TestAlert(
        apaths.path,
        schema_map,
        drop_cutouts=True,
        mock_modules=None,
        # mock_modules=["SuperNNova"],
        serialize=TestAlert.guess_serializer(topic),
    )

Load an alert as a dictionary for local testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use this alert dictionary to test your code locally with real data.

.. code-block:: python

    alert_dict = talert.data["dict"]

Integration test using a single alert
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After deploying your module, run an integration test with a single alert.

First, publish an alert as a message to your module's trigger topic.

.. code:: python

    publish_pubsub(
        topic,
        message=talert.msg_payload,
        attrs=talert.mock.attrs,
    )

Then, pull a message from the subscription to the output topic.

.. code:: python

    msgs = pull_pubsub(subscrip, max_messages=1)  # list
    alert_dict_out = decode_alert(msgs[0])

    alert_dict_out  # look at the message to see if it is as-expected

Integration test using a batch of alerts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Do a full integration test.

First, publish a batch of alerts.
Explicitly create and use a Pub/Sub publisher client to avoid instantiating a new one
for every alert.
Keep a list of published alert IDs to validate against in the next step.

Publish:

.. code-block:: python

    from google.cloud import pubsub_v1
    publisher = pubsub_v1.PublisherClient()
    i_max = 100  # limit the max number of alerts published

   published_alert_ids = []
   for i, path in enumerate(apaths.gen()):
       talert = TestAlert(
           apaths.path,
           schema_map,
           drop_cutouts=True,
           mock_modules=None,
           # mock_modules=["SuperNNova"],
           serialize=TestAlert.guess_serializer(topic),
       )

       publish_pubsub(
           topic,
           message=talert.msg_payload,
           attrs=talert.mock.attrs,
           publisher=publisher,
       )

       published_alert_ids.append(talert.ids)

       if i > i_max:
           break

Wait to give the alerts time to make their way through the pipeline.
About 5 seconds per module should be plenty.

Then, use the ``IntegrationTestValidator`` to pull messages from the subscription and
validate their alert IDs with those that were published in the previous step.

.. code:: python

    validator = IntegrationTestValidator(subscrip, published_alert_ids, schema_map)
    success = validator.run()

If everything worked as expected, the validator will report ``success = True``.
