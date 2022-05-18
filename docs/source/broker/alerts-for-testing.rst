Alerts for Testing
===================

Instructions for accessing and working with alerts for testing purposes.

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

Load an alert as a dictionary
------------------------------

Once you load the alert into a dictionary you can use it to test pieces of your function locally.

.. code-block:: python

   from broker_utils import data_utils, schema_maps

   # choose a survey
   SURVEY = "ztf"
   # SURVEY = "elasticc"

   # load the survey's schema map
   schema_map = schema_maps.load_schema_map('generic', False, SURVEY)

   # get a generator that returns paths to individual avro files
   paths = data_utils.test_alert_avro_paths(survey=SURVEY)

   # get the path to a single file
   path = next(paths)

   # load the alert as a dictionary
   alert_dict = data_utils.load_alert(path, 'dict', schema_map=schema_map, drop_cutouts=True)

   # the dict can also be loaded by instantiating a TestAlert object as follows
   # this will be useful in the next section
   test_alert = data_utils.TestAlert(path, schema_map)
   alert_dict = test_alert.data["dict"]


Publish alerts to a Pub/Sub topic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

	If you plan to perform an integration test by publishing alerts and then pulling messages from a subscription after they've been processed, it is recommended that you first purge the subscription to make sure it contains no extraneous messages before you begin.
    This can be accomplished using ``gcp_utils.purge_subscription("subscrip")`` where ``subscrip`` is the subscription name.

.. code-block:: python

   from collections import namedtuple
   from google.cloud import pubsub_v1
   from broker_utils import data_utils, gcp_utils, schema_maps
   from broker_utils.data_utils import TestAlert

   # fill these in with your own options
   SURVEY = ""  # ztf or elasticc
   TESTID = ""
   topic_name_stub = ""  # topic to publish the alert to

   # dummy can be used to generate dummy results for a pipeline module and
   # attach them to the message
   dummy = None
   # dummy = ["SuperNNova"]

   # set these verbatim
   publisher = pubsub_v1.PublisherClient()
   schema_map = schema_maps.load_schema_map('generic', False, SURVEY)
   topic = f"{SURVEY}-{topic_name_stub}-{TESTID}"
   publish_as = TestAlert.guess_publish_format(topic)

   # publish every alert in the directory to Pub/Sub
   # keep a list of ids for later comparison
   published_alert_ids = []
   i_max = 100  # limit the max number of alerts published
   for i, path in enumerate(data_utils.test_alert_avro_paths(survey=SURVEY)):
       test_alert = TestAlert(path, schema_map)
       gcp_utils.publish_pubsub(
           topic,
           message=test_alert.create_msg_payload(publish_as=publish_as, dummy=dummy),
           attrs=test_alert.create_msg_attrs(),
           publisher=publisher
       )
       published_alert_ids.append(test_alert.ids)
       if i > i_max:
           break

Pull alerts from a Pub/Sub subscription
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you completed the previous section and want to check the output of whatever module processed the messages you published, you can do so with the following code.
It will pull messages from a Pub/Sub subscription and compare the Ids with those in `published_alerts`.
Note that the subscription must already exist.

.. code:: python

   # fill this in with the name of the subscription
   subscrip_name_stub = ""

   # set this verbatim (unless your subscription does not follow this naming convention)
   subscrip = f"{SURVEY}-{subscrip_name_stub}-{TESTID}"

   # pull messages and compare the ids with those published earlier
   pulled_msg_ids = TestAlert.pull_and_compare_ids(subscrip, published_alert_ids, schema_map)
