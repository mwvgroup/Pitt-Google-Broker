# SuperNNova doesn't seem to be saving results to BigQuery. What's going on?

```python
table = "metadata"
today = "2021-10-13"
query = f"""
    SELECT objectId, candid, publish_time__SuperNNova AS pt
    FROM `{project_id}.{dataset}.{table}`
    WHERE DATE(publish_time__SuperNNova) >= '{today}'
"""
metadf = gcp_utils.query_bigquery(query).to_dataframe()


candid = 1746528292515015009  # single candid from metadf
table = "SuperNNova"
query = f"""
    SELECT *
    FROM `{project_id}.{dataset}.{table}`
    WHERE candid={candid}
"""
snndf = gcp_utils.query_bigquery(query).to_dataframe()
# this is empty. confirms that results are not being saved.
```

Added logging to the Cloud Function. Now test it.

```python
import json
from python_fncs.pubsub_consumer import Consumer
from python_fncs.cast_types import avro_to_dict
from base64 import b64decode, b64encode

# get an alert
consumer = Consumer("ztf-loop")
msgs = consumer.stream_alerts(parameters={"max_results": 1, "max_backlog": 1})
alert_dict = avro_to_dict(msgs[0].data)
alert_dict = {k: v for k, v in alert_dict.items() if "cutout" not in k}
# publish it
gcp_utils.publish_pubsub("ztf-exgalac_trans_cf", alert_dict)
# pull down SuperNNova's output message
msgs = gcp_utils.pull_pubsub("ztf-SuperNNova-counter")
msg_dict = json.loads(msgs[0])  # this looks exactly as expected.
# query from bigquery table
candid = alert_dict["candid"]
table = "SuperNNova"
query = f"""
    SELECT *
    FROM `{project_id}.{dataset}.{table}`
    WHERE candid={candid}
"""
testdf = gcp_utils.query_bigquery(query).to_dataframe()
```

- did this 3 times
- insert rows to bigquery was successful
- Output Pub/Sub message looks as expected.
- now it's crashing because it doesn't have enough memory
- i don't understand...?
