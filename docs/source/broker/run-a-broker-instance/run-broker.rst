Run the Broker
==============

-  `Start the Broker`_
-  `Stop the Broker`_
-  `Options for Ingesting Alerts`_

   -  `Kafka Topic Syntax`_

Use this document to run a broker instance manually (typically a Testing
instance).

See also:

- :doc:`test-an-instance`
- :doc:`../components/auto-scheduler` to schedule a
  (typically Production) instance to run automatically each night.
- :doc:`../components/night-conductor`
- :ref:`View and Access Resources <broker/run-a-broker-instance/view-resources>`

--------------

Start the Broker
----------------

The two VMs (consumer and night-conductor) can be started manually using the code below.
Start-up scripts are configured during broker setup. They are stored in the
``broker_files`` Cloud Storage bucket, and the address is added to the instance's
metadata using the key ``startup-script-url``.
To start a VM without triggering the start-up script, unset the startup script url.
See :ref:`View and Access Resources: Compute Engine VMs <broker/run-a-broker-instance/view-resources:Compute Engine VMs>`.

Components running on Cloud Functions or Cloud Run are always on, listening for alerts.

.. code-block:: bash

    # Example VM name (used below):
    survey=ztf
    testid=mytestid
    vm_name="${survey}-consumer-${testid}"
    # vm_name="${survey}-night-conductor-${testid}"

    # Optional: set the consumer to use non-default Kafka and/or Pub/Sub topics
    # Example topic names (used below):
    KAFKA_TOPIC_FORCE=""                                # default, today's topic (UTC)
    # KAFKA_TOPIC_FORCE="ztf_20220302_programid1"       # Kafka topic from Mar 2, 2022
    PS_TOPIC_FORCE=""                                   # default alerts Pub/Sub topic
    # PS_TOPIC_FORCE="my-alerts"                        # Pub/Sub topic named my-alerts
    # Set the topics as metadata:
    metadata="KAFKA_TOPIC_FORCE=${KAFKA_TOPIC_FORCE},PS_TOPIC_FORCE=${PS_TOPIC_FORCE}"
    gcloud compute instances add-metadata "$vm_name" \
          --metadata="${metadata}"

    # Start the VM:
    gcloud compute instances start "${vm_name}"

Stop the Broker
---------------

The two VMs (consumer and night-conductor) can be stopped manually using the code below.
Components running on Cloud Functions or Cloud Run are always on.

.. code-block:: bash

    # Example VM name (used below):
    vm_name="ztf-consumer-testid"
    # vm_name="ztf-night-conductor-testid"

    # Optional: reset the consumer VM's Kafka and/or Pub/Sub topics to defaults
    # Example topic names (used below):
    KAFKA_TOPIC_FORCE=""                                # default, today's topic (UTC)
    PS_TOPIC_FORCE=""                                   # default alerts Pub/Sub topic
    # Set the topics as metadata:
    metadata="KAFKA_TOPIC_FORCE=${KAFKA_TOPIC_FORCE},PS_TOPIC_FORCE=${PS_TOPIC_FORCE}"
    gcloud compute instances add-metadata "$vm_name" \
          --metadata="${metadata}"

    # Stop the VM:
    gcloud compute instances stop "${vm_name}"

--------------

Options for Ingesting Alerts
----------------------------

You have three options to get alerts into the broker. Production
instances typically use #1; **testing instances typically use #3**.

1. Connect to a **live stream**. Obviously, this can only be done at
   night when there is a live stream to connect to. If there are no
   alerts in the topic, the consumer will poll repeatedly for available
   topics and begin ingesting when its assigned topic becomes active.
   Use the `Kafka Topic Syntax`_ with today's date (UTC timezone).

2. Connect to a **stream from a previous night**
   This is not recommended since alerts will *flood* into the
   broker as the consumer ingests as fast as it can. For ZTF, you can
   check
   `ztf.uw.edu/alerts/public/ <https://ztf.uw.edu/alerts/public/>`__;
   ``tar`` files larger than 74 (presumably in bytes) indicate dates
   with >0 alerts. Use the `Kafka Topic Syntax`_ with a date within the last 7 days.

3. Use the **consumer simulator** to *control the flow* of alerts into the broker.
   Leave the consumer VM off.
   See :doc:`consumer-simulator` for details.

Kafka Topic Syntax
~~~~~~~~~~~~~~~~~~

Topic name syntax:

-  ZTF: ``ztf_yyyymmdd_programid1`` where ``yyyymmdd`` is replaced with
   the date.
-  DECAT: ``decat_yyyymmdd_2021A-0113`` where ``yyyymmdd`` is replaced
   with the date.
