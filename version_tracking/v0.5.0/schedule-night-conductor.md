# Schedule Night Conductor

Cloud Scheduler cron job -> Pub/Sub -> Cloud Function -> start VM

- [Cloud Scheduler] Define a schedule on which Pub/Sub messages will be published
- [Pub/Sub]
- [Cloud Function] `cue_night_conductor`: listens to a PS topic, sets metadata on `night-conductor`, starts `night-conductor`

- [Scheduling compute instances with Cloud Scheduler](https://cloud.google.com/scheduler/docs/start-and-stop-compute-engine-instances-on-a-schedule)
    - replace their CF with our own
- [Python Examples for Cloud Function]
    - [Set Metadata](https://cloud.google.com/compute/docs/reference/rest/v1/instances/setMetadata#examples)
    - [Start Instance](https://cloud.google.com/compute/docs/reference/rest/v1/instances/start#examples)


Test the Pub/Sub message:
```python
import base64
from pgb_utils import pubsub as pgbps
survey="ztf"
testid="v050"

topic_name = f'{survey}-cue_night_conductor-{testid}'
cue = b'START'
# cue = base64.b64encode('START'.encode('utf-8'))
fut = pgbps.publish(topic_name, cue)

msg = pgbps.pull(topic_name, msg_only=False)
```
