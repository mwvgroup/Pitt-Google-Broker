Deploying a Consumer
====================

This documentation demonstrates how to schedule the Pitt-Google Broker to
automatically launch and ingest alerts. Alert consumption is run using the
Google Compute Engine service. In order to ensure alerts are completely
ingested for a given night, two instances are scheduled for each consumer.
Each instance runs for ~2 days and instances are restarted on alternating days.

The ``stream_GCS_to_BQ`` function must be deployed from the command line as a
Google Cloud Function so that it listens to the appropriate bucket(s) for new
alert Avro files and appends the data to a BigQuery table. The Google Cloud SDK
must be installed first (see above). The following script automates the
deployment. Note that it may take a couple of minutes to complete.

.. code-block::bash
    :linenos:

    ./broker/deploy_cloudfnc.sh

Scheduling Alert Ingestion
--------------------------

Start by creating the instance that will be run.

.. code-block:: bash

   gcloud compute instances create-with-container consume-ztf-1 \
       --zone=us-central1-a \  # Physical region to host machine from
       --machine-type=f1-micro \  # Type of machine to use (impacts machine resources and cost)
       --image-project=cos-cloud \  # The boot image / opperating system for the instance
       --container-image=[HOSTNAME]/[PROJECT-ID]/[IMAGENAME] \  # container image name to pull onto VM instance
       --labels=env=consume-ztf-1 \  # List of label KEY=VALUE pairs to add
       --image=cos-stable-81-12871-69-0  # See ``gcloud compute images list`` for options

   gcloud compute instances create-with-container consume-ztf-2 \
       --zone=us-central1-a \
       --machine-type=f1-micro \
       --image-project=cos-cloud \
       --container-image=[HOSTNAME]/[PROJECT-ID]/[IMAGENAME] \
       --labels=env=consume-ztf-2 \
       --image=cos-stable-81-12871-69-0

.. note:: If you need to undo this step use the
   ``gcloud compute instances delete [INSTANCE]`` command.

Create the Pub/Sub topics to trigger starting and stopping the instance

.. code-block:: bash

   gcloud pubsub topics create start-instance-event
   gcloud pubsub topics create stop-instance-event

.. note:: If you need to undo this step use the
   ``gcloud functions delete [TOPIC]`` command.

Next, create the cloud functions to publish to PubSub

.. code-block:: bash

   cd broker/cloud_functions/scheduleinstance/

   gcloud functions deploy startInstancePubSub \
       --trigger-topic start-instance-event \
       --runtime nodejs8

   gcloud functions deploy stopInstancePubSub \
       --trigger-topic stop-instance-event \
       --runtime nodejs8

Finally, create the start and end jobs.

.. code-block:: bash

   # Reset consume-ztf-1 on odd days
   gcloud scheduler jobs create pubsub stop-consume-ztf-1 \
       --schedule '0 9 1-31/2 * *' \
       --topic stop-instance-event \
       --message-body '{"zone":"us-west1-b", "label":"env=consume-ztf-1"}' \
       --time-zone 'America/Los_Angeles'

   gcloud scheduler jobs create pubsub start-consume-ztf-1 \
       --schedule '0 17 1-31/2 * *' \
       --topic start-instance-event \
       --message-body '{"zone":"us-west1-b", "label":"env=consume-ztf-1"}' \
       --time-zone 'America/Los_Angeles'

   # Reset consume-ztf-2 on even days
   gcloud scheduler jobs create pubsub stop-consume-ztf-2 \
       --schedule '0 0 2-30/2 * *' \
       --topic stop-instance-event \
       --message-body '{"zone":"us-west1-b", "label":"env=consume-ztf-2"}' \
       --time-zone 'America/Los_Angeles'

   gcloud scheduler jobs create pubsub start-consume-ztf-2 \
       --schedule '0 0 2-30/2 * *' \
       --topic start-instance-event \
       --message-body '{"zone":"us-west1-b", "label":"env=consume-ztf-2"}' \
       --time-zone 'America/Los_Angeles'
