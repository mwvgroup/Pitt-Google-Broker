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

.. note::

    This section contains instructions to manually start the consumer VM.
    Cloud Functions and Cloud Run are always on; they do not need to be started or stopped.
    If you are running a test and do not need the consumer VM, you can skip this section.

Fill in the broker instance keywords below with the same ones used to deploy the broker instance.

.. code-block:: bash

    survey=
    testid=

If you want the consumer to use non-default Kafka and/or Pub/Sub topics, set the appropriate ``TOPIC_FORCE`` variable in the VM's metadata.
The code below gives examples.
These will be automatically unset when the VM shuts down.

.. code-block:: bash

    KAFKA_TOPIC_FORCE=""                                # default, today's topic (UTC)
    # KAFKA_TOPIC_FORCE="ztf_20220302_programid1"       # Kafka topic from Mar 2, 2022

    PS_TOPIC_FORCE=""                                   # default alerts Pub/Sub topic
    # PS_TOPIC_FORCE="my-alerts"                        # Pub/Sub topic named my-alerts

    # Set the topics as metadata:
    metadata="KAFKA_TOPIC_FORCE=${KAFKA_TOPIC_FORCE},PS_TOPIC_FORCE=${PS_TOPIC_FORCE}"
    gcloud compute instances add-metadata "$vm_name" --metadata="${metadata}"

Start the consumer VM.

.. note::

    Note that the consumer will automatically try to connect to the survey and begin ingesting alerts. If you want to avoid this, set the startup script url to an empty string in the VM's metadata.
    See :ref:`View and Access Resources: Compute Engine VMs <broker/run-a-broker-instance/view-resources:Compute Engine VMs>`.

.. code-block:: bash

    vm_name="${survey}-consumer-${testid}"
    gcloud compute instances start "${vm_name}"

Stop the Broker
---------------

.. note::

    This section contains instructions to manually stop the consumer VM.
    Cloud Functions and Cloud Run are always on; they do not need to be started or stopped.

.. code-block:: bash

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
