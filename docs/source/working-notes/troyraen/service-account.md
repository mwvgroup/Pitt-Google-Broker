# Create a Service Account and Download Credentials

References:

- [Creating a Service Account](https://cloud.google.com/iam/docs/creating-managing-service-accounts#creating)
- [Creating and managing service account keys](https://cloud.google.com/iam/docs/creating-managing-service-account-keys)
- [Understanding roles](https://cloud.google.com/iam/docs/understanding-roles), also contains a list of roles and definitions.

<!-- - https://cloud.google.com/iam/docs/granting-changing-revoking-access
- https://cloud.google.com/iam/docs/manage-access-other-resources
    - bigquery has a separate sdk: https://cloud.google.com/bigquery/docs/reference/bq-cli-reference#bq_add-iam-policy-binding
- https://cloud.google.com/iam/docs/understanding-roles#predefined
- https://cloud.google.com/sdk/gcloud/reference/resource-manager -->

## Setup

```bash
GOOGLE_CLOUD_PROJECT="project-id"
GOOGLE_APPLICATION_CREDENTIALS="path/to/GCP_auth_key.json"
SERVICE_ACCOUNT_NAME="my-account"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
# Try to avoid the owner role, but here it is for convenience.
# Pick something more specific using the link above.
ROLE="roles/owner"
```

## Create a service account:

If you are accessing a new project (or perhaps deactivated previous settings)
you'll need to connect `gcloud` to the project via a
user account (e.g. a Gmail address) that has access.
If you are not accessing a new project, you likely do not need to do this.

```bash
gcloud init
# follow prompts and connect to the project
```

```bash
# Create the service account
gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME"

# Assign the service account a role, which gives it permissions
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="$ROLE"

# Create and download an auth key file
gcloud iam service-accounts keys create "$GOOGLE_APPLICATION_CREDENTIALS" \
    --iam-account="$SERVICE_ACCOUNT"
```

## Switch the Service Account your API calls use

This activates the service account for `gcloud` and `bq` calls:

```bash
gcloud auth activate-service-account \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
```

To activate for Python calls, you just need to set the environment variables
`GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS`.
