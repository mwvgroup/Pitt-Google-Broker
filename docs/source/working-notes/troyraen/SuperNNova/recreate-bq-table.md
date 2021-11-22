Changed column name pred_class -> predicted_class.
Want to change name in production instance without losing data.

- [x]  copy SuperNNova table to a backup (from Console)
- [ ]  query data from backup to dataframe
- [ ]  delete and recreate the production table
- [ ]  change the dataframe column name and load to the new table


Delete and recreate production table
```bash
cd /Users/troyraen/Documents/broker/snn/broker/setup_broker
survey=ztf
test_dataset=test
test_table=SuperNNova_backup
prod_dataset=ztf_alerts
prod_table=SuperNNova

# copy it
bq cp ${prod_dataset}.${prod_table} ${test_dataset}.${test_table}
# make sure can query from backup in python below

# delete it
bq rm --table ${prod_dataset}.${prod_table}

# recreate it
bq mk --table ${prod_dataset}.${prod_table} templates/bq_${survey}_${prod_table}_schema.json
```

Query data from backup, change column name, load to production table
```python
from broker_utils import gcp_utils
import os

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
test_dataset = 'test'
test_table = 'SuperNNova_backup'
prod_dataset = 'ztf_alerts'
prod_table = 'SuperNNova'

# query from backup
query = (
    f'SELECT * '
    f'FROM `{project_id}.{test_dataset}.{test_table}` '
)
query_job = gcp_utils.query_bigquery(query)
df = query_job.to_dataframe()

# change col name
df['predicted_class'] = df['pred_class']

# load to production table
gcp_utils.load_dataframe_bigquery(f'{prod_dataset}.{prod_table}', df)
```
