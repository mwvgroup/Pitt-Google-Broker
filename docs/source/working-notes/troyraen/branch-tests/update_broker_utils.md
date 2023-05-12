# update_broker_utils

## Setup

```bash
survey=ztf
testid=brokerutils
```

```python
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
survey, testid = "ztf", "brokerutils"
```

## Deploy instance

```bash
cd broker/setup_broker
teardown=False
./setup_broker.sh "$testid" "$teardown" "$survey"
```

## Publish test alerts

Following [Alerts for Testing](https://pitt-broker.readthedocs.io/en/develop/broker/alerts-for-testing.html).

```python
from collections import namedtuple
from datetime import datetime
import os
import re
from pathlib import Path
import yaml
from google.cloud import pubsub_v1
from broker_utils import data_utils, gcp_utils

# GCP project that the gcp_utils module connects to
gcp_utils.pgb_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
# Cloud Storage bucket that holds test alerts
testing_bucket_id = "ztf-test_alerts"

# Set alert_dir to a local path for alert storage
alert_dir = Path("/Users/troyraen/Documents/broker/Pitt-Google/testing/docs/source/working-notes/troyraen/alerts-for-testing")

def _get_avro_paths(dir):
    """Return a generator of paths to Avro files in the directory `dir`."""
    return (p for p in dir.glob('*.avro'))
paths = _get_avro_paths(alert_dir)
path = next(paths)

survey, testid = "ztf", "brokerutils"
topic_name = f"{survey}-alerts-{testid}"
publisher = pubsub_v1.PublisherClient()

# define two helper functions
FName = namedtuple("FName", ["objectId", "candid", "kafka_topic", "avro"])
def parse_fname(fin: str):
    return FName._make(fin.split('.'))

def match_name_stub(resource_name: str, name_stub: str):
    """Regex match `resource_name`, `name_stub` accounting for broker name syntax."""
    rexp = fr"(\w*[-_])({name_stub})(.*)"
    if isinstance(resource_name, pd.Series):
        # call regex on each element in Series
        return resource_name.str.match(rexp)
    return re.match(rexp, resource_name)

def publish_alert(path, topic_name):
    # determine if the topic name stub is "alerts" and set variables accordingly
    # if so, we'll publish Avro-serialized bytes
    # else we'll publish JSON bytes
    is_alerts = bool(match_name_stub(topic_name, "alerts"))
    if is_alerts:
        return_as = "bytes"  # Pub/Sub publishes as bytes-encoded, Avro-serialized
        kwargs = {}
    else:
        return_as = "dict"  # Pub/Sub publishes as bytes-encoded, JSON
        kwargs = {
            "drop_cutouts": True,
            "schema_map": alert_dir / "ztf-schema-map.yaml"
        }

    # create dummy attributes to attach
    attrs = {
        "kafka_topic": parse_fname(path.name).kafka_topic,
        "kafka_timestamp": str(datetime.utcnow())
    }

    # load the alert and publish
    alert = data_utils.load_alert(path, return_as, **kwargs)
    result = gcp_utils.publish_pubsub(
        topic_name, alert, attrs=attrs, publisher=publisher
    )
    return result

# publish a single alert to Pub/Sub
publish_alert(path, topic_name)

# publish every alert in the directory to Pub/Sub
for path in _get_avro_paths(alert_dir):
    publish_alert(path, topic_name)
```

Wait a bit for things to process, then cue night conductor to collect metadata

```bash
NIGHT="END"
vm_name="${survey}-night-conductor-${testid}"
gcloud compute instances add-metadata "$vm_name" \
          --metadata "NIGHT=${NIGHT}"
gcloud compute instances start "$vm_name"
```

## Query test results

According to the [README](https://pitt-broker.readthedocs.io/en/develop/working-notes/troyraen/alerts-for-testing/README.html) included with the test alerts, we expect:

- 37 alerts to pass all filters and show up in the SuperNNova table
- 13 alerts will not pass all filters and will not show up in the SuperNNova table

```python
import os
import pandas as pd

import setup_gcp as sup

dataset = f"{survey}_alerts_{testid}"
fin = "/Users/troyraen/Documents/broker/Pitt-Google/onboarding/docs/source/broker/onboarding/alerts-for-testing/alerts-for-testing.csv"
df_expect = pd.read_csv(fin)
datasets = sup._resources("BQ", survey, testid)  # dict(str(dataset): [str(table),])
# buckets = sup._resources("GCS", survey, testid)

as_expected = {}  # dict(str(dataset.table): bool(result is as expected))
for dataset, tables in datasets.items():
    for table in tables:
        compare = ["objectId", "candid"]    # fields to compare in dataframes
        select = compare                    # columns to query
        # we'll use more info from the metadata table
        if table == "metadata":
            compare = select + ["kafka_topic__alerts", "filename__alert_avros"]
            select = mycompare + ["bucketId__alert_avros"]

        df = gcp_utils.query_bigquery((
            f"SELECT {', '.join(my_select)} "
            f"FROM `{project_id}.{dataset}.{table}`"
        )).to_dataframe()

        # validate results
        as_expect = True
        if table == "metadata":
            as_expect = bool(
                match_name_stub(df["bucketId__alert_avros"], "alert_avros")
            )
        as_expected[f"{dataset}.{table}"] = (
            as_expect & df[compare].equals(df_expect[compare])
        )


```

## broker-utils not installing on night-conductor

Solution: use a Conda environment with Python 3.7

```bash
# shart over with a fresh vm
survey=ztf
testid=brokerutils
vm_name="${survey}-night-conductor-${testid}"
gcloud compute instances stop "$vm_name"
gcloud compute instances delete "$vm_name"
machinetype=e2-standard-2
gcloud compute instances create "$vm_name" \
    --machine-type="$machinetype" \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true
# log in
gcloud compute instances start "$vm_name"
gcloud compute ssh "$vm_name"
# install pip3 and screen
apt-get update
apt-get install -y python3-pip screen
# then install pgb-broker-utils==0.2.28
pip3 install pgb-broker-utils==0.2.28 &> install_broker_utils_0.2.28.out
# this does not succeed
# astropy requires jinja2 which requires MarkupSafe.soft_unicode
# but this was removed in v2.1.0
# https://markupsafe.palletsprojects.com/en/2.1.x/changes/#version-2-1-0
# go back to local machine and the download the log file to this directory
exit
gcloud compute scp "troyraen@${vm_name}:/home/troyraen/install_broker_utils_0.2.28.out" .

gcloud compute instances add-metadata --zone="$zone" "$vm_name" \
    --metadata "ATTRIBUTE1=${ATTRIBUTE1},ATTRIBUTE2=${ATTRIBUTE2}"


wget https://repo.anaconda.com/archive/Anaconda3-2021.05-Linux-x86_64.sh
bash Anaconda3-2021.05-Linux-x86_64.sh

conda create -n pgb python=3.7
conda activate pgb

pip install pgb-broker-utils==0.2.28
```

Night conductor's environment is python 3.7.3.
More info about the VM environment is in the file install_broker_utils_0.2.28.out
in this directory.

I tried installing pinned versions of all requirements
(obtained by successfully installing broker-utils in a clean environment on a
Mac, Big Sur, python 3.7.10), with astropy last.
Everything installed but astropy, which failed with the same error.

*WILL HAVE TO USE A CONDA ENVIRONMENT. IT WORKS.*
