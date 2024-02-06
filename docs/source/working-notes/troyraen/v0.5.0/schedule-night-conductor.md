# docs/source/working-notes/troyraen/v0.5.0/schedule-night-conductor.md

## Schedule Night Conductor

Cloud Scheduler cron job -> Pub/Sub -> Cloud Function -> start VM

- [Cloud Scheduler] Define a schedule on which Pub/Sub messages will be published
- [Pub/Sub]
- [Cloud Function] `cue_night_conductor`: listens to a PS topic, sets metadata on `night-conductor`, starts `night-conductor`

- [Scheduling compute instances with Cloud Scheduler](https://cloud.google.com/scheduler/docs/start-and-stop-compute-engine-instances-on-a-schedule)
    - replace their CF with our own
- [Python Examples for Cloud Function]
    - [Set Metadata](https://cloud.google.com/compute/docs/reference/rest/v1/instances/setMetadata#examples)
    - [Start Instance](https://cloud.google.com/compute/docs/reference/rest/v1/instances/start#examples)


```bash
export GCP_PROJECT=$GOOGLE_CLOUD_PROJECT
export TESTID=v050
export SURVEY=ztf
export ZONE="us-central1-a"
```

Test the Pub/Sub message:
```python
# import base64
from pgb_utils import pubsub as pgbps
survey="ztf"
testid="v050"

topic_name = f'{survey}-cue_night_conductor-{testid}'
# topic_name = 'test'
cue = b'START'
attrs = {'topic_date': 'False'}
# cue = base64.b64encode('START'.encode('utf-8'))
fut = pgbps.publish(topic_name, cue, attrs=attrs)

msg = pgbps.pull(topic_name, msg_only=False)

attrs = msg[0][0].message.attributes
```
