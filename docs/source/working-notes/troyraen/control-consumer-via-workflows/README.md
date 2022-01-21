# Use GCP Workflows and Cloud Build to create and start the consumer VM

1. create an instance template for the consumer VM
2. create a consumer VM from the template
3. start the consumer VM with configs to listen to desired survey stream

Some of the above steps are defined and described in [consumer-instance-template/README.md](consumer-instance-template/README.md).

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
