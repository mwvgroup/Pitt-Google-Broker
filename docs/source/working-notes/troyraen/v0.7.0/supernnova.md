# Implementing SuperNNova Classifier

SuperNNova Links:
- [docs](https://supernnova.readthedocs.io/en/latest/index.html)
- [github](https://github.com/supernnova/SuperNNova)
- [arXiv paper](https://arxiv.org/pdf/1901.06384.pdf)  

The following is mostly code to develop and test and Cloud Function.
This uses a pre-trained model provided by the SuperNNova team.

## Preliminary exploration

Following [run_onthefly.py](https://github.com/supernnova/SuperNNova/blob/master/run_onthefly.py)

```bash
pip install supernnova
pip install torch
pip install h5py
pip install natsort
pip install scikit-learn
pip install seaborn
```

Get some alerts and classify them:

```python
from astropy.time import Time
import numpy as np
import pandas as pd
from pgb_utils import pubsub as pgbps
from supernnova.validation.validate_onthefly import classify_lcs

COLUMN_NAMES = [
    "SNID",
    "MJD",
    "FLUXCAL",
    "FLUXCALERR",
    "FLT"
]
cols = ['objectId', 'jd', 'magpsf', 'sigmapsf', 'magzpsci', 'fid']
ztf_fid_names = {1:'g', 2:'r', 3:'i'}

device='cpu'
model_file='/Users/troyraen/Documents/broker/SNN/ZTF_DMAM_V19_NoC_SNIa_vs_CC_forFink/vanilla_S_0_CLF_2_R_none_photometry_DF_1.0_N_global_lstm_32x2_0.05_128_True_mean.pt'
# rnn_state = torch.load(model_file, map_location=lambda storage, loc: storage)

subscription = 'ztf-loop'
msgs = pgbps.pull(subscription, max_messages=10)
# dflist = [pgbps.decode_ztf_alert(m, return_format='df') for m in msgs]
dflist = []
for m in msgs:
    df = pgbps.decode_ztf_alert(m, return_format='df')
    df['objectId'] = df.objectId
    df = df[cols]

    df['SNID'] = df['objectId']
    df['MJD'] = Time(df['jd'], format='jd').mjd
    df['FLUXCAL'] = 10 ** ((df['magzpsci'] - df['magpsf']) / 2.5)
    df['FLUXCALERR'] = df['FLUXCAL'] * df['sigmapsf'] * np.log(10 / 2.5)
    df['FLT'] = df['fid'].map(ztf_fid_names)

    dflist.append(df)
dfs = pd.concat(dflist)

ids_preds, pred_probs = classify_lcs(dfs, model_file, device)
preds_df = reformat_to_df(pred_probs, ids=ids_preds)



def reformat_to_df(pred_probs, ids=None):
    """ Reformat SNN predictions to a DataFrame
    # TO DO: suppport nb_inference != 1
    """
    num_inference_samples = 1

    d_series = {}
    for i in range(pred_probs[0].shape[1]):
        d_series["SNID"] = []
        d_series[f"prob_class{i}"] = []
    for idx, value in enumerate(pred_probs):
        d_series["SNID"] += [ids[idx]] if len(ids) > 0 else idx
        value = value.reshape((num_inference_samples, -1))
        value_dim = value.shape[1]
        for i in range(value_dim):
            d_series[f"prob_class{i}"].append(value[:, i][0])
    preds_df = pd.DataFrame.from_dict(d_series)

    # get predicted class
    preds_df["pred_class"] = np.argmax(pred_probs, axis=-1).reshape(-1)

    return preds_df
```


## Test the Cloud Function pieces locally

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

### Classify known Ia

The docs indicate that "usually" class0 indicates a Ia and class1 indicates non-Ia,
but this will depend on how the model was trained.

I (Troy) checked by classifying a recent observation of the known Ia that I recently
pulled from file storage to send to Ella (SN_2021rhu aka ZTF21abiuvdk, [ZTF21abiuvdk_lightcurve.png](ZTF21abiuvdk_lightcurve.png) and compare with
[Alerce](https://alerce.online/object/ZTF21abiuvdk)).

Results indicate the opposite of expected... SN_2021rhu is assigned to class1 with
high confidence.

Adding this to my list of questions for Anais about the trained model.

```python
import main
from broker_utils import data_utils, gcp_utils

snIa = 'ZTF21abiuvdk'
fname = '/Users/troyraen/Documents/broker/ella/avros/ZTF21abiuvdk.1664460940815015004.ztf_20210723_programid1.avro'

alert_dict = data_utils.decode_alert(fname)
snn_dict = main.classify_with_snn(alert_dict)
snn_dict
# output is:
{'objectId': 'ZTF21abiuvdk',
 'candid': 1664460940815015004,
 'prob_class0': 0.04458457976579666,
 'prob_class1': 0.9554154872894287,
 'pred_class': 1}
```

## Local, full test

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

## Deploy Cloud Function

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
