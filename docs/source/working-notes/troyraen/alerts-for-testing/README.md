# alerts-for-testing: Alerts for Testing Purposes

There are 50 alert avro files in this directory:

```python
>>> fnames_pass_all  # these 37 pass all science filters, fitters, and classifiers
['ZTF21abrtszs.1704252770815015016.ztf_20210901_programid1.avro',
 'ZTF18aamyaaj.1704217901015015001.ztf_20210901_programid1.avro',
 'ZTF18abjivac.1704166204715015005.ztf_20210901_programid1.avro',
 'ZTF18aazyhkf.1704216964315015009.ztf_20210901_programid1.avro',
 'ZTF21abprzfg.1704377621415015002.ztf_20210901_programid1.avro',
 'ZTF18abfiprz.1704210683715015008.ztf_20210901_programid1.avro',
 'ZTF18abfcjtr.1704264951715015018.ztf_20210901_programid1.avro',
 'ZTF18ablpgeh.1704168636115015025.ztf_20210901_programid1.avro',
 'ZTF18abmvvoi.1704210214315015007.ztf_20210901_programid1.avro',
 'ZTF21abpiosb.1704227924715015016.ztf_20210901_programid1.avro',
 'ZTF21aavuqzr.1704237176015015021.ztf_20210901_programid1.avro',
 'ZTF18abiyatb.1704255124815015005.ztf_20210901_programid1.avro',
 'ZTF18abcprzp.1704241945915015014.ztf_20210901_programid1.avro',
 'ZTF18abgflsz.1704167673715015035.ztf_20210901_programid1.avro',
 'ZTF21abngbrl.1704376211815015000.ztf_20210901_programid1.avro',
 'ZTF19aayvyfa.1704368802315015006.ztf_20210901_programid1.avro',
 'ZTF21abiblpl.1704232151015015001.ztf_20210901_programid1.avro',
 'ZTF18abjeatz.1704218432515015007.ztf_20210901_programid1.avro',
 'ZTF21abfoyac.1704213531415015021.ztf_20210901_programid1.avro',
 'ZTF18abmvrcs.1704169570415015040.ztf_20210901_programid1.avro',
 'ZTF18abmsrfx.1704189471615015091.ztf_20210901_programid1.avro',
 'ZTF21abvicne.1704287286115015016.ztf_20210901_programid1.avro',
 'ZTF21abpkpuy.1704173816015015004.ztf_20210901_programid1.avro',
 'ZTF18aawznqy.1704242400615015006.ztf_20210901_programid1.avro',
 'ZTF19aatvxcs.1704167674515015003.ztf_20210901_programid1.avro',
 'ZTF21abvbbnf.1704262850915015014.ztf_20210901_programid1.avro',
 'ZTF18aawmdot.1704269301615015026.ztf_20210901_programid1.avro',
 'ZTF21abvawaj.1704264473315015001.ztf_20210901_programid1.avro',
 'ZTF18abbjkcd.1704220844315015006.ztf_20210901_programid1.avro',
 'ZTF21abeoaio.1704203375215015000.ztf_20210901_programid1.avro',
 'ZTF18abccouv.1704170984015015001.ztf_20210901_programid1.avro',
 'ZTF18aaqzpsv.1704174284215015008.ztf_20210901_programid1.avro',
 'ZTF21abvyxhc.1704226970115015009.ztf_20210901_programid1.avro',
 'ZTF21abvawaj.1704227453315015003.ztf_20210901_programid1.avro',
 'ZTF18abaihuj.1704182991215015011.ztf_20210901_programid1.avro',
 'ZTF18aboetso.1704167675315015038.ztf_20210901_programid1.avro',
 'ZTF18abmmdyk.1704238580315015013.ztf_20210901_programid1.avro']

>>> fnames_pass_none  # these 13 pass no science filters, fitters, or classifiers
['ZTF18abltebw.1703211072815015018.ztf_20210831_programid1.avro',
 'ZTF18abefmzp.1703203221815015027.ztf_20210831_programid1.avro',
 'ZTF18abhmmsr.1703210603215015172.ztf_20210831_programid1.avro',
 'ZTF18ablxccg.1703210122915015070.ztf_20210831_programid1.avro',
 'ZTF18abkizda.1703209665915015001.ztf_20210831_programid1.avro',
 'ZTF18abeajfh.1703207002015015001.ztf_20210831_programid1.avro',
 'ZTF18abstrxn.1703210605915010075.ztf_20210831_programid1.avro',
 'ZTF18abvorxt.1703231753215015030.ztf_20210831_programid1.avro',
 'ZTF18acyizaa.1703222170415010089.ztf_20210831_programid1.avro',
 'ZTF18abtvahq.1703232236315010002.ztf_20210831_programid1.avro',
 'ZTF18abtuzwd.1703232234115010019.ztf_20210831_programid1.avro',
 'ZTF18abeoiol.1703210126115010063.ztf_20210831_programid1.avro',
 'ZTF18abbwsvo.1703210606215015045.ztf_20210831_programid1.avro']
```

## The code that retrieved the files:

```python
from broker_utils import data_utils, gcp_utils

project_id = "ardent-cycling-243415"
dataset = "ztf_alerts"
table = "metadata"
bucket_id = "ztf-alert_avros"
kafka_topic = "ztf_20210901_programid1"
```

Find and download alerts that pass all filters

```python
query = (
    f"SELECT * "
    f"FROM `{project_id}.{dataset}.{table}` "
    f"WHERE publish_time__alerts_pure IS NOT NULL "
    f"AND kafka_topic__alerts='{kafka_topic}' "
    f"LIMIT 50"
)
query_job = gcp_utils.query_bigquery(query)
df = query_job.to_dataframe()
d = df.dropna()

fnames_pass_all = d.filename__alert_avros.tolist()
localdir = "/Users/troyraen/Documents/broker/repotroy/troy/alerts-for-testing"
for f in fnames:
    gcp_utils.cs_download_file(localdir, bucket_id, f)
```

Find and download alerts that pass no filters/classifiers, but do pass everything else

```python
query = (
    f"SELECT * "
    f"FROM `{project_id}.{dataset}.{table}` "
    f"WHERE publish_time__alerts_pure IS NULL "
    # f"AND kafka_topic__alerts='{kafka_topic}' "
    f"LIMIT 10000"
)
query_job = gcp_utils.query_bigquery(query)
df = query_job.to_dataframe()

# drop alerts that passed any filters
d = df.dropna(axis=1, how="all")
null_cols = [
    "publish_time__exgalac_trans",
    "publish_time__salt2",
    "publish_time__SuperNNova",
    "publish_time__exgalac_trans_cf",
]
d = d.loc[d[null_cols].isnull().all(1)]

# drop alerts that did not pass something else
non_null_cols = [c for c in d.columns if c not in null_cols]
d = d.dropna(subset=non_null_cols)

# download
fnames_pass_none = d.sample(13).filename__alert_avros.tolist()
for f in fnames_pass_none:
    gcp_utils.cs_download_file(localdir, bucket_id, f)
```
