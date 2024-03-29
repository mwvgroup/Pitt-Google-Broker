Setup the Broker
================

-  `Prerequisites`_
-  `Setup the Broker Instance`_

   -  `Upload Kafka Authentication Files`_

-  `What does setup_broker.sh do?`_

--------------

Prerequisites
-------------

First, complete the :doc:`initial-setup` to setup your
Google Cloud project and install the SDKs. Make sure your environment
variables are set:

.. code:: bash

    # If you installed the SDKs to a Conda environment, activate it.
    export GOOGLE_CLOUD_PROJECT=ardent-cycling-243415
    export GOOGLE_APPLICATION_CREDENTIALS=<path/to/GCP/credentials.json>

--------------

Setup the Broker Instance
--------------------------

.. code:: bash

    # Clone the repo and navigate to the setup directory
    git clone https://github.com/mwvgroup/Pitt-Google-Broker
    cd Pitt-Google-Broker/broker/setup_broker

    # Setup a broker instance
    survey=ztf  # ztf or decat
    testid=mytest  # replace with your choice of testid
    teardown=False  # False to create resources
    version="3.3"  # avro schema version of incoming alerts
    use_authentication=false  # whether the consumer VM should use an authenticated connection

    # setup all GCP resources for a broker instance
    ./setup_broker.sh "${testid}" "${teardown}" "${survey}" "${version}" "${use_authentication}"

See :doc:`../broker-overview` for a description of ``survey``, ``testid``,
``version`` (which gets transformed to a ``versiontag``), and ``use_authentication``.
When the Avro schema changes, a new `alerts_{versiontag}` table and bucket need to be created,
and the `versiontag` environment variable on all Cloud Functions needs to be updated.

See `What does setup_broker.sh do?`_ for details about the script itself.

Upload Kafka Authentication File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note: This is not necessary if using an unauthenticated connection.

Note: Do this before the consumer VM finishes its install and shuts
itself down. Else, you'll need to start it again (see
:ref:`here <broker/run-a-broker-instance/view-resources:Compute Engine VMs>`).

The consumer VM requires a "keytab" authorization file in order to create an authenticated
connection to the Kafka broker. *This must be obtained independently and uploaded to the VM
manually, stored at the following location:*

- pitt-reader.user.keytab, at VM path
   /home/broker/consumer/pitt-reader.user.keytab

You can use the ``gcloud compute scp`` command for this:

.. code:: bash

    survey=ztf  # use the same survey used in broker setup
    testid=mytest  # use the same testid used in broker setup
    zone=us-central1-a  # use the VM's zone

    gcloud compute scp pitt-reader.user.keytab "${survey}-consumer-${testid}:/home/broker/consumer/pitt-reader.user.keytab" --zone="${zone}"

--------------

What does setup_broker.sh do?
---------------------------------

Resource name stubs are given below in brackets []. See :doc:`../broker-instance-keywords` for details.

1. Create and configure GCP resources in BigQuery, Cloud Storage,
   Dashboard, and Pub/Sub. Print a URL to the instance's Dashboard for
   the user. (You may be asked to authenticate yourself using
   ``gcloud auth login``; follow the instructions. If you don't have a
   bigqueryrc config file setup yet it will walk you through
   creating one.)

2. Upload the directors broker/beam, broker/broker\_utils/schema\_maps,
   broker/consumer, and broker/night\_conductor to the Cloud Storage
   bucket broker_files].

3. Create and configure the Compute Engine instances
   night-conductor] and consumer].
   with start/stop schedules. Disable the schedules on testing brokers.

4. Create Cloud Scheduler cron jobs cue_night_conductor_START]
   and cue_night_conductor_END] to check that the VM's start/stop as expected.
   Print the schedule and the code needed to change
   it. If this is a Testing instance, pause the jobs and print the code
   needed to resume them.

5. Configure Pub/Sub notifications (topic alert_avros]) on the
   Cloud Storage bucket alert_avros] that stores the alert Avro.

6. Create a VM firewall rule to open the port used by ZTF's Kafka
   stream. This step will *fail* because the rule already exists and we
   don't need a separate rule for testing resources. *You can ignore
   it.*

7. Deploy Cloud Functions.
