# gcloud Examples<a name="gcloud-examples"></a>

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [gcloud Examples](#gcloud-examples)
  - [Setup](#setup)
  - [BigQuery](#bigquery)
  - [Cloud Functions](#cloud-functions)
  - [Cloud Run](#cloud-run)
  - [Cloud Storage](#cloud-storage)
  - [Compute Engine](#compute-engine)
    - [Compute Engine Schedule](#compute-engine-schedule)
  - [Pub/Sub](#pubsub)
  - [Service account](#service-account)

<!-- mdformat-toc end -->

External reference:

- [Google's `gcloud` CLI reference](https://cloud.google.com/sdk/gcloud/reference)

## Setup<a name="setup"></a>

The following variables are used in many of the examples on this page.
Set them to your own preferences.

[Broker Instance Keywords](../../broker/broker-instance-keywords.rst):

```bash
SURVEY="ztf"
TESTID="mytest"
```

[Environment variables](pittgoogle-client.rtfd.io/pubsub/docs/source/overview/env-vars.html):

```bash
export GOOGLE_CLOUD_PROJECT="avid-heading-329016"  # this is our development project
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/GCP_auth_key.json"
```

Default zone/region when creating VMs and other compute-related resources:

```bash
export CLOUDSDK_COMPUTE_REGION='us-central1'
export CLOUDSDK_COMPUTE_ZONE='us-central1-a'
```

## BigQuery<a name="bigquery"></a>

Create a dataset

```bash
dataset_name="my-dataset"   # choose a name for your dataset

# Create the dataset
# bq library comes with gcloud
bq mk --dataset "${GOOGLE_CLOUD_PROJECT}:dataset_name" \
    --location="${REGION}"
```

## Cloud Functions<a name="cloud-functions"></a>

```bash
CF_name="my-cloud-function"     # choose a name for your Cloud Function
entry_point="run"               # fill in name of module's entry-point function
trigger_topic="my-topic"        # fill in name of Pub/Sub topic that will trigger your function

# deploy. run this command from within the directory containing your Cloud Function
gcloud functions deploy "${CF_name}" \
    --entry-point "${entry_point}" \
    --runtime python37 \
    --trigger-topic "$trigger_topic" \
    --set-env-vars TESTID="${TESTID}",SURVEY="${SURVEY}"

# delete
gcloud functions delete "${CF_name}"
```

## Cloud Run<a name="cloud-run"></a>

- [Instructions to create resources with pubsub trigger](https://cloud.google.com/run/docs/triggering/pubsub-push#command-line)

Initialize variables

```bash
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
PROJECT_NUMBER=$(gcloud projects list \
        --filter="$(gcloud config get-value project)" \
        --format="value(PROJECT_NUMBER)" \
    )

# name for the Run service you're deploying, and related resources
NAME_STUB="xmatch_AbrilCVs"
NAME_STUB_LOWER_DASH="xmatch-abrilcvs"
NAME="${SURVEY}-${NAME_STUB}"
NAME_LOWER_DASH="${SURVEY}-${NAME_STUB_LOWER_DASH}"
if [ "$TESTID" != "False" ]; then
    NAME="${NAME}-${TESTID}"
    NAME_LOWER_DASH="${NAME_LOWER_DASH}-${TESTID}"
fi

# service account with permissions to invoke Cloud Run
SERVICE_ACCOUNT_NAME="cloud-run-invoker"
DISPLAYED_SERVICE_ACCOUNT_NAME="Cloud Run Invoker Service Account"
SERVICE_ACCOUNT_ADDRESS="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# container image
IMAGE_URL="gcr.io/${PROJECT_ID}/${NAME_LOWER_DASH}:latest"

# Get the endpoint from Run deployment output (below),
# and be sure to add the `route` to the end of the url
# (assigned in your Run code via the tag `@app.route()`)
ENDPOINT=""

# Pub/Sub
TOPIC = "${SURVEY}-alerts"  # trigger topic
TOPIC_PROJECT="ardent-cycling-243415"  # project that owns the topic
SUBSCRIPTION="${TOPIC}-${NAME_STUB}"  # push subscription, to be attached to trigger topic
if [ "$TESTID" != "False" ]; then
    TOPIC="${TOPIC}-${TESTID}"
    SUBSCRIPTION="${SUBSCRIPTION}-${TESTID}"
fi
ACK_DEADLINE=300
```

Deploy cloud run

```bash
# cd into the directory with the Run code
# cd /Users/troyraen/Documents/broker/abril/broker/cloud_run/abril_cv

# create and upload container
gcloud builds submit --tag "$IMAGE_URL"
# deploy to cloud run
gcloud run deploy "$NAME_LOWER_DASH" --image "$IMAGE_URL"  \
    --no-allow-unauthenticated \
    --set-env-vars GCP_PROJECT="$PROJECT_ID",TESTID="$TESTID",SURVEY="$SURVEY"
# This returns a Service URL that you will need in the following steps.
# Set the variable:
# ENDPOINT="${service_url}${route}"
# where `route` is assigned in your Run code via the tag `@app.route()`
# Example service URL: https://xmatch-allwise-3tp3qztwza-uc.a.run.app
```

Allow Pub/Sub to create authentication tokens in the project:

```bash
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountTokenCreator"
```

Create a service account and give it permission to invoke cloud run.
Alternately, you can re-use an existing service account, just add the policy binding.

```bash
gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name "$DISPLAYED_SERVICE_ACCOUNT_NAME"

gcloud run services add-iam-policy-binding "$NAME_LOWER_DASH" \
    --member=serviceAccount:"$SERVICE_ACCOUNT_ADDRESS" \
    --role=roles/run.invoker
```

Create the subscription with the service account attached

```bash
gcloud pubsub subscriptions create "$SUBSCRIPTION" \
    --topic "$TOPIC" \
    --topic-project="$TOPIC_PROJECT" \
    --push-endpoint="$ENDPOINT" \
    --push-auth-service-account="$SERVICE_ACCOUNT_ADDRESS" \
    --ack-deadline="$ACK_DEADLINE"
```

## Cloud Storage<a name="cloud-storage"></a>

Download the avro file for a single alert:

```bash
bucket="${GOOGLE_CLOUD_PROJECT}-${survey}-alert_avros"
filename="<objectId>.<sourceId>.<kafkaTopic>.avro"
# filename="100000238.200000476050.elasticc-2022fall.avro"
local_dir="/<path>/<to>/<local>/<dir>"
gsutil cp "gs://${bucket}/${filename}" ${local_dir}/.
```

## Compute Engine<a name="compute-engine"></a>

### Compute Engine Schedule<a name="compute-engine-schedule"></a>

Create a schedule (only needs to be done once)
[unix-cron format](https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules)

```bash
schedule_name="my-schedule"     # choose schedule name
start_schedule="* * * * *"      # choose start time. (UTC, unix-cron format, link above)
stop_schedule="* * * * *"       # choose stop time. (UTC, unix-cron format, link above)
description="schedule"          # fill in a description

gcloud compute resource-policies create instance-schedule "${schedule_name}" \
    --description="${description}" \
    --vm-start-schedule="${start_schedule}" \
    --vm-stop-schedule="${stop_schedule}" \
    --timezone="UTC"
```

Attach/unattach a schedule to a VM

```bash
vm_name="my-vm"                 # set this to the VM name
schedule_name="my-schedule"     # set this to the schedule name

# Attach schedule
gcloud compute instances add-resource-policies "${nconductVM}" \
    --resource-policies="${nconductVMsched}"

# Unattach schedule
gcloud compute instances remove-resource-policies "${nconductVM}" \
    --resource-policies="${nconductVMsched}"
```

## Pub/Sub<a name="pubsub"></a>

- [https://cloud.google.com/sdk/gcloud/reference/pubsub](https://cloud.google.com/sdk/gcloud/reference/pubsub)

```bash
# create topic
TOPIC="mytopic"
gcloud pubsub topics create "$TOPIC"

# create subscription
SUBSCRIPTION="mysubscription"
TOPIC="mytopic"
TOPIC_PROJECT=$GOOGLE_CLOUD_PROJECT
gcloud pubsub subscriptions create "$SUBSCRIPTION" \
    --topic="$TOPIC" \
    --topic-project="$TOPIC_PROJECT"
```

## Service account<a name="service-account"></a>

See also [service-account.md](service-account.md).

```bash
NAME="tjraen-owner"
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
FILE_NAME_STUB="GCP_auth_key-user_test.json"
FILE_NAME="/Users/troyraen/Documents/broker/repo/${FILE_NAME_STUB}"

gcloud config set project $PROJECT_ID

gcloud iam service-accounts create "$NAME"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/owner"
gcloud iam service-accounts keys create "$FILE_NAME" \
    --iam-account="${NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
```
