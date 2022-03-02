# Deploy Abril CVs cross match to GCP project `pitt-google-broker-user-test`

```bash
export GOOGLE_CLOUD_PROJECT="avid-heading-329016"
export GOOGLE_APPLICATION_CREDENTIALS="/Users/troyraen/Documents/broker/repo/GCP_auth_key-user_test.json"
```

Initialize variables

```bash
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
PROJECT_NUMBER=$(gcloud projects list \
        --filter="$(gcloud config get-value project)" \
        --format="value(PROJECT_NUMBER)" \
    )

# broker instance keywords
SURVEY="ztf"
TESTID="False"

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

# Get the endpoint from Run deployment output,
# and be sure to add the `route` to the end of the url
# (assigned in your Run code via the tag `@app.route()`)
ENDPOINT="https://ztf-xmatch-abrilcvs-f7cwgvzqrq-uc.a.run.app/abrilcv"

# Pub/Sub
TOPIC="ztf-loop"  # trigger topic
# TOPIC="${SURVEY}-alerts"  # trigger topic
TOPIC_PROJECT="ardent-cycling-243415"  # project that owns the topic
SUBSCRIPTION="${TOPIC}-${NAME_STUB}"  # push subscription, to be attached to trigger topic
if [ "$TESTID" != "False" ]; then
    TOPIC="${TOPIC}-${TESTID}"
    SUBSCRIPTION="${SUBSCRIPTION}-${TESTID}"
fi
ACK_DEADLINE=300
```

Follow instructions in [../gcloud-exmples.md](../gcloud-exmples.md) to create the
resources and deploy the service.

Create additional resources:

```bash
# pubsub topic the module publishes
PUB_TOPIC="${SURVEY}-${NAME_STUB}"
gcloud pubsub topics create "$PUB_TOPIC"
# subscribe to that topic
gcloud pubsub subscriptions create "$PUB_TOPIC" --topic "$PUB_TOPIC"

# bigquery table
TEMPLATE_DIR="/Users/troyraen/Documents/broker/abril/broker/setup_broker/templates"
DATASET="${SURVEY}_alerts"
TABLE="xmatch"
bq mk --dataset "${PROJECT_ID}:${DATASET}"
bq mk --table "${PROJECT_ID}:${DATASET}.${TABLE}" \
    "${TEMPLATE_DIR}/bq_${SURVEY}_${TABLE}_schema.json"
```
