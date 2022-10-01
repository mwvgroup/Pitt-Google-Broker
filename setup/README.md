# Setup Broker

## Deploy

Note: This assumes you've already run [setup_project.sh](setup_project.sh) at least once in your project.

To deploy a broker instance, cd into this directory and do:

```bash
testid="testid"  # TODO: customize
testid="raenpreprod"
survey="elasticc"
teardown="False"

./setup_broker.sh "${testid}" "${teardown}" "${survey}"
```

While the consumer's install script is still running*, complete the following.

A keytab file is required for authentication to the Kafka server.
It must be uploaded to the consumer manually and then moved into place.
`cd` into a directory containing the file `pitt-reader.user.keytab`, then run:

```bash
consumerVM="${survey}-consumer-${testid}"
keytab="pitt-reader.user.keytab"

gcloud compute scp "${keytab}" "${consumerVM}:~/${keytab}"
gcloud compute ssh "${consumerVM}" -- sudo mv "~/${keytab}" "/home/broker/consumer/${keytab}"
```

\*If the consumer shuts down before you do this, unset its startup script and then turn it back on and upload the keyfile. Be sure to reset the startup script. This can be done at anytime after you've turned the consumer back on (the point at which it checks for one).

After the consumer shuts down, complete the following.

The consumer install requires a larger machine size than its every-day operations will.
Change the machine size to something smaller:

```bash
gcloud compute instances set-machine-type "${consumerVM}" --machine-type="g1-small"
```

## Test

To test the consumer, unset the startup script (see instructions above), `ssh` in, manually run the part of the startup script that polls for a list of topics, and inspect the results.

To test other modules, publish several test alerts into their trigger topic(s).
Then inspect the results. (Expected results differ by module.)
Here's an example that just publishes one message to the main `alerts` topic:

```python
from broker_utils import gcp_utils as gcp

testid = "testid"  # TODO: customize
testid = "raenpreprod"
survey = "elasticc"

# load a message for testing
sub = f"{survey}-loop"
msgs = gcp.pull_pubsub(sub, msg_only=False)
msg = msgs[0].message

# publish the message
topic = f"{survey}-alerts-{testid}"
gcp.publish_pubsub(topic, msg.data, attrs=msg.attributes)
```
