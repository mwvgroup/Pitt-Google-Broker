# pitt-google-broker-billing

- [Export Cloud Billing data to BigQuery](https://cloud.google.com/billing/docs/how-to/export-data-bigquery)

- Billing project:
    - Name: pitt-google-broker-billing
    - ID: light-cycle-328823
- Billing account: 0102E2-E3A6BA-C2AFD5


## Create a new service account

```bash

NAME="tjraen-owner"
PROJECT_ID="light-cycle-328823"
FILE_NAME="/Users/troyraen/Documents/broker/repo/GCP_auth_key-broker_billing.json"

gcloud init
# gcloud config set compute/region us-central1
# gcloud config set compute/zone ZONE us-central1-a

gcloud iam service-accounts create "$NAME"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/owner"
gcloud iam service-accounts keys create "$FILE_NAME" \
    --iam-account="${NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
```

## Run some queries

```bash
pip install --upgrade pyarrow
pip uninstall pyarrow
pip install pyarrow==0.17.1
```

```python
import os
from broker_utils import gcp_utils
import queries

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')  # ardent-cycling-243415
billing_project_id = os.getenv('GOOGLE_CLOUD_PROJECT2')  # light-cycle-328823

query, job_config = queries.where_date(lookback=30)
billdf = gcp_utils.query_bigquery(
    query, job_config=job_config, project_id=billing_project_id
).to_dataframe()

query, job_config = queries.count_alerts_by_date(lookback=30)
countdf = gcp_utils.query_bigquery(
    query, job_config=job_config, project_id=project_id
).to_dataframe()

date = "2021-10-09"
query, job_config = queries.count_alerts_by_date(date=date, lookback=None)
count9df = gcp_utils.query_bigquery(
    query, job_config=job_config, project_id=project_id
).to_dataframe()
```
