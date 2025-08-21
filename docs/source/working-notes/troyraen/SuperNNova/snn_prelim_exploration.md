# docs/source/working-notes/troyraen/SuperNNova/snn_prelim_exploration.md

## SuperNNova preliminary exploration

(see also: [snn_train_a_model.md](snn_train_a_model.md))

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
