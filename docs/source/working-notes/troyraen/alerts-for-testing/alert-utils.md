# Alert Utils

The live version of this document has been moved into the documentation ([Alerts for Testing](docs/source/broker/alerts-for-testing.rst)).
We leave the original version below, for reference.

This file contains various python functions to work with a set of test alerts.
It relies on our broker-utils library which can be installed using `pip install pgb-broker-utils`.
(You may want to activate a Conda environment before installing.)

## Setup

```python
import os
from pathlib import Path
import yaml

from google.cloud import pubsub_v1

from broker_utils import data_utils, gcp_utils

# GCP project that the gcp_utils module connects to
gcp_utils.pgb_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
# Cloud Storage bucket that holds test alerts
testing_bucket_id = "ztf-test_alerts"

# Set alert_dir to a local path for alert storage
alert_dir = Path(
    "/Users/troyraen/Documents/broker/Pitt-Google/testing/docs/source/working-notes/troyraen/alerts-for-testing"
)
os.mkdir(alert_dir)


def _get_avro_paths(dir):
    """Return a generator of paths to Avro files in the directory `dir`."""
    return (p for p in dir.glob("*.avro"))
```

## Download the set of test alerts

```python
# download the files
gcp_utils.cs_download_file(alert_dir, testing_bucket_id)
```

## Load an alert as a dict

Once you load the alert into a dictionary you can use it to test pieces of your function locally.

```python
paths = _get_avro_paths(alert_dir)  # generator returning file paths one at a time
path = next(paths)  # path to a single file

# full alert packet, including cutouts
alert_dict = data_utils.decode_alert(str(path), return_as="dict")

# alert packet, excluding cutouts
# we need to pass in a schema map
fschema_map = alert_dir / "ztf-schema-map.yaml"
with open(fschema_map, "rb") as f:
    schema_map = yaml.safe_load(f)  # dict
alert_dict = data_utils.decode_alert(
    str(path),
    return_as="dict",
    schema_map=schema_map,
    drop_cutouts=True,
)
```

## Publish alert to a topic

```python
# fill in a topic name
topic_name = ""
# choose the format your function expects the the alert to be in
format = "json"
format = "avro"
# instantiate a client to publish alerts
publisher = pubsub_v1.PublisherClient()

# define two helper functions: load_alert and publish_alert
def publish_alert(path, topic_name, format):
    alert = load_alert(path, format)
    result = gcp_utils.publish_pubsub(topic_name, alert, publisher=publisher)


def load_alert(path, format):
    """Load alert from file at `path` and return in format `format`."""
    if format == "avro":
        # we want to publish the alert in Avro format,
        # so we just need to read in the bytes from the file
        with open(path, "rb") as fin:
            alert = fin.read()

    elif format == "json":
        # we want to publish the alert in Json format,
        # so we load the alert as a dict, dropping the cutouts
        # (keeping the cutouts will throw an error because they are not
        # encoded properly using json. must use avro for cutouts)
        fschema_map = alert_dir / "ztf-schema-map.yaml"
        with open(fschema_map, "rb") as f:
            schema_map = yaml.safe_load(f)  # dict
        alert = data_utils.decode_alert(
            str(path),
            return_as="dict",
            schema_map=schema_map,
            drop_cutouts=True,
        )

    return alert


# publish every alert in the directory to Pub/Sub
for path in _get_avro_paths(alert_dir):
    publish_alert(path, topic_name, format)
```
