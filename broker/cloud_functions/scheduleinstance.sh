#!/bin/sh

# Create 2 instances of the consumer

gcloud compute instances create-with-container consume-ztf-1 \
    --zone=us-central1-a \  # Physical region to host machine from
    --machine-type=f1-micro \  # Type of machine to use (impacts machine resources and cost)
    --image-project=cos-cloud \  # The boot image / opperating system for the instance
    --container-image=gcr.io/ardent-cycling-243415/consume_ztf \  # container image name to pull onto VM instance
    --labels=env=consume-ztf-1 \  # List of label KEY=VALUE pairs to add
    --image=cos-stable-81-12871-69-0  # See ``gcloud compute images list`` for options

gcloud compute instances create-with-container consume-ztf-2 \
    --zone=us-central1-a \
    --machine-type=f1-micro \
    --image-project=cos-cloud \
    --container-image=gcr.io/ardent-cycling-243415/consume_ztf \
    --labels=env=consume-ztf-2 \
    --image=cos-stable-81-12871-69-0


# Create the Pub/Sub topics to trigger starting and stopping the instance
gcloud pubsub topics create start-instance-event
gcloud pubsub topics create stop-instance-event


# Create the cloud functions to publish to PubSub

cd broker/cloud_functions/scheduleinstance/

gcloud functions deploy startInstancePubSub \
    --trigger-topic start-instance-event \
    --runtime nodejs8

gcloud functions deploy stopInstancePubSub \
    --trigger-topic stop-instance-event \
    --runtime nodejs8

# Finally, schedule the PubSub messages that trigger the cloud functions.

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
