# Connect Pitt-Google to the Rubin alert stream testing deployment

December 2021

Details and access credentials were sent to us by Eric Bellm via email.
Spencer Nelson provided some additional details specific to our Kafka Connect consumer.
Here are some links for reference:

- Connecting: https://github.com/lsst-dm/sample_alert_info#obtaining-the-data-with-kafka
- Schemas: https://alert-schemas-int.lsst.cloud/
- `consumer.properties` config file example: https://github.com/lsst-dm/sample_alert_info/tree/main/examples/alert_stream_integration_endpoint/java_console_consumer
- Using schema registry with Kafka Connect: https://docs.confluent.io/platform/7.0.1/schema-registry/connect.html. Spencer says, "Our stream uses Avro for the message values, not keys (we don't set the key to anything in particular), so you probably want the `value.converter` properties."
- Tools and libraries for VOEvents: https://wiki.ivoa.net/twiki/bin/view/IVOA/IvoaVOEvent#Tools_and_Libraries


## Create a service account for Workflows

```bash
SERVICE_ACCOUNT_NAME="workflows"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME"

ROLE="roles/logging.logWriter"
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="$ROLE"

ROLE="roles/compute.admin"
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="$ROLE"
```

## Create Consumer VM

Deploy and Trigger workflow:

```bash
# deploy
gcloud workflows deploy rubin-workflow --source=workflows.yaml \
    --service-account="${SERVICE_ACCOUNT}"

# run
# if TESTID is not null, it should begin with "-"
ARGS='{"SURVEY": "rubin", "TESTID": "", "GOOGLE_CLOUD_PROJECT": "ardent-cycling-243415"}'
gcloud workflows run rubin-workflow --data=${ARGS}
```

SSH in:

```bash
gcloud compute ssh VM_NAME --container CONTAINER_NAME
```
