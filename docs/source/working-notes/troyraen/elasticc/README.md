# ELAsTiCC Challenge

## Alert Format

Reference links:

- [The DESC ELAsTiCC Challenge - Alert Schema](https://portal.nersc.gov/cfs/lsst/DESC_TD_PUBLIC/ELASTICC/#alertschema)

The alerts will be schemaless.
Thus we must pre-load the schema in order to deserialize the alert.
broker_utils has been updated to handle this.
Let's test it.

```python
from broker_utils.data_utils import open_alert
```

<!-- ```python
import fastavro

v = "elasticc.v0_9"
format = "avsc"
schema = "alert"
# schema = "brokerClassification"
aschema = fastavro.schema.load_schema(f"{v}.{schema}.{format}")
``` -->

Open an alert from file (note that the schema is attached):

```python
from broker_utils.testing import AlertPaths

apaths = AlertPaths("elasticc")
alert_dict = open_alert(apaths.path)
alert_dict.keys()
```

Pull and open an alert from the elasticc-loop stream.
Alerts in this stream came from an Elasticc (Kafka) test stream, not from a file.
These messages are schemaless, which we must tell `open_alert`.

```python
from broker_utils.gcp_utils import pull_pubsub

subscrip = "elasticc-loop"
msgs = pull_pubsub(subscrip)
alert_bytes = msgs[0]

# load_schema = True                        # try all the schemas broker_utils knows about
load_schema = "elasticc.v0_9.alert.avsc"  # use a specific schema. faster.

alert_dict = open_alert(alert_bytes, load_schema=load_schema)
alert_dict.keys()
```

Test a Cloud Function:

```python
from broker_utils.gcp_utils import publish_pubsub

topic = "troy-test"  # this triggers a cloud fnc called test-elasticc-type
# you can try it yourself, or
# you can use your own cloud function's trigger topic
publish_pubsub(topic, alert_bytes)
```
