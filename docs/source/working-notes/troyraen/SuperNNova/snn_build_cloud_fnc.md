# docs/source/working-notes/troyraen/SuperNNova/snn_build_cloud_fnc.md

## SuperNNova - build, deploy, test the Cloud Function

### Test the Cloud Function pieces locally

```bash
export GCP_PROJECT=$GOOGLE_CLOUD_PROJECT
export TESTID=False
export SURVEY=ztf
cd /Users/troyraen/Documents/broker/repo3/broker/cloud_functions/classify_snn
```

```python
import main
from broker_utils import gcp_utils

msg = gcp_utils.pull_pubsub('ztf-alerts-reservoir', msg_only=False)[0]

alert_dict = data_utils.decode_alert(msg.data)
dropcols = ['cutoutScience', 'cutoutTemplate', 'cutoutDifference']
alert_dict = {k: v for k, v in alert_dict.items() if k not in dropcols}
snn_dict = main.classify_with_snn(alert_dict)

gcp_utils.publish_pubsub('test', {'alert': alert_dict, 'SuperNNova': snn_dict})
snn_msg = gcp_utils.pull_pubsub('test')[0]

gcp_utils.insert_rows_bigquery(bq_table, [snn_dict])
```

### Local, full test

```bash
conda create -n snn python=3.7
conda activate snn

export 'GOOGLE_APPLICATION_CREDENTIALS=/Users/troyraen/Documents/broker/repo/GCP_auth_key.json'
export GCP_PROJECT='ardent-cycling-243415'
export TESTID='False'
export SURVEY='ztf'

cd '/Users/troyraen/Documents/broker/repo3/broker/cloud_functions/classify_snn'
pip install -r requirements.txt
pip install ipython
# cd '/Users/troyraen/Documents/broker/repo3/broker/broker_utils'
# python -m pip install -e .

ipython
```

```python
from broker_utils import data_utils, gcp_utils
import main

# create alert as it would come from the ex-galac stream
msg = gcp_utils.pull_pubsub('ztf-alerts-reservoir')[0]
alert_dict_tmp = data_utils.decode_alert(msg)
dropcols = ['cutoutScience', 'cutoutTemplate', 'cutoutDifference']
alert_dict = {k: v for k, v in alert_dict_tmp.items() if k not in dropcols}

# publish it and pull it back down
gcp_utils.publish_pubsub('test', alert_dict)
msgs_exgalac = gcp_utils.pull_pubsub('test', msg_only=False)
msg_exgalac = msgs_exgalac[0].message

# run cloud function: classify, publish pubsub, load bigquery
main.run(msg_exgalac, {})

# check results
# pull pubsub
msg_snn = gcp_utils.pull_pubsub('ztf-SuperNNova-sub')[0]
snn_dicts = data_utils.decode_alert(msg_snn)
# query bigquery
candid = snn_dicts['alert']['candid']
query = (
    f'SELECT * '
    f'FROM `ardent-cycling-243415.ztf_alerts.SuperNNova` '
    f'WHERE candid={candid} '
)
snn_queryjob = gcp_utils.query_bigquery(query)
for r, row in enumerate(snn_queryjob):
    print(row)
```
This works.

### Deploy Cloud Function

```bash
survey="ztf"
testid="False"
classify_snn_CF_name="${survey}-classify_with_SuperNNova"
classify_snn_trigger_topic="${survey}-exgalac_trans"
classify_snn_entry_point="run"
cd '/Users/troyraen/Documents/broker/repo3/broker/cloud_functions/classify_snn'

gcloud functions deploy "$classify_snn_CF_name" \
    --entry-point "$classify_snn_entry_point" \
    --runtime python37 \
    --trigger-topic "$classify_snn_trigger_topic" \
    --set-env-vars TESTID="$testid",SURVEY="$survey"
```

This errors out with:

```
ERROR: (gcloud.functions.deploy) OperationError: code=3, message=Build failed: Build error details not available.Please check the logs at https://console.cloud.google.com/cloud-build/builds;region=us-central1/d782dfbb-285d-44aa-a164-040e48660089?project=591409139500. Please visit https://cloud.google.com/functions/docs/troubleshooting#build for in-depth troubleshooting documentation for build related errors.
```

I cannot find any more specific info in the logs or at the provided links.
The step that it fails on is called "uploading_python_pkg_layer".

Verified I can successfully deploy a different cloud function.

```bash
survey="ztf"
testid="False"
classify_snn_CF_name="troy-test-check_cue_response"
classify_snn_trigger_topic="${survey}-exgalac_trans"
classify_snn_entry_point="run"
cd '/Users/troyraen/Documents/broker/repo3/broker/cloud_functions/check_cue_response'

gcloud functions deploy "$classify_snn_CF_name" \
    --entry-point "$classify_snn_entry_point" \
    --runtime python37 \
    --trigger-topic "$classify_snn_trigger_topic" \
    --set-env-vars TESTID="$testid",SURVEY="$survey"
```

Try a different deployment method... use Cloud Build directly.
```bash
gcloud builds submit --config \
    /Users/troyraen/Documents/broker/repo3/version_tracking/v0.7.0/cloud_build.yaml \
    /Users/troyraen/Documents/broker/repo3/broker/cloud_functions/classify_snn
```

Same result.

Comment everything out of the Cloud Function and put things back one by one until it
fails.

Ok, the problem is `torch` and the fact that Cloud Functions don't have support for GPU libraries.
See [here](https://stackoverflow.com/questions/55449313/google-cloud-function-python-3-7-requirements-txt-makes-deploy-fail).

Fixed by providing a direct URL in requirements.txt.

### Test changes to broker utils

```bash
cd /Users/troyraen/Documents/broker/snn/broker/broker_utils
python -m pip install -e .
```
```python
from broker_utils import data_utils, gcp_utils
schema_map = schema_maps.load_schema_map('ztf', False)

fname = '/Users/troyraen/Documents/broker/troy/troy/SNN/ZTF21abiuvdk/ZTF21abiuvdk.1707409520815015012.ztf_20210904_programid1.avro'
alert_dict = data_utils.alert_avro_to_dict(fname)
# looks good
df = data_utils.alert_dict_to_dataframe(alert_dict, schema_map)
# looks good

alert_dict = data_utils._drop_cutouts(alert_dict, schema_map)
gcp_utils.publish_pubsub('test', alert_dict)
# success, pull it back down and check
msgs = gcp_utils.pull('test')
ad = data_utils.decode_alert(msgs[0])
# looks good
```
