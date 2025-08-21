# docs/source/working-notes/troyraen/AbrilCVs/exporation_for_linea_talk.md

## Exploration for LIneA talk - Dec 2, 2021

```python
from matplotlib import pyplot as plt
import os
import pandas as pd
from astropy.coordinates import SkyCoord
from google.cloud import bigquery
import broker_utils as bu

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
dir = "/Users/troyraen/Documents/broker/Pitt-Google/troy/docs/source/working-notes/troyraen/AbrilCVs"
fcat_condensed = f"{dir}/J_MNRAS_492_L40/catalog_condensed.dat"

abrildf = pd.read_csv(fcat_condensed)

types = ('Type1', 'Type2')
fig, (ax1, ax2)= plt.subplots(1,2)
for t, ax in zip(types, (ax1, ax2)):
    abrildf[t].value_counts().plot(kind='bar', ax=ax)
    ax.set_title(t)
plt.show(block=False)


query  = "SELECT objectId, candid, jd, fid, magpsf, sigmapsf FROM `ardent-cycling-243415.ztf_alerts.DIASource` WHERE objectId='ZTF18abcccnr'"
bq_client = bigquery.Client(project=project_id)
query_job = bq_client.query(query)
df = query_job.to_dataframe()
```


```python
def query_bigquery(
    query: str,
    project_id: Optional[str] = None,
    job_config: Optional[bigquery.job.QueryJobConfig] = None,
) -> bigquery.job.QueryJob:
    """Query BigQuery.

    Example query:
        ``
        query = (
            f'SELECT * '
            f'FROM `{project_id}.{dataset}.{table}` '
            f'WHERE objectId={objectId} '
        )
        ``

    Example of working with the query_job:
        ``
        for r, row in enumerate(query_job):
            # row values can be accessed by field name or index
            print(f"objectId={row[0]}, candid={row['candid']}")
        ``
    """
    if project_id is None:
        project_id = pgb_project_id

    bq_client = bigquery.Client(project=project_id)
    query_job = bq_client.query(query, job_config=job_config)

    return query_job

```
