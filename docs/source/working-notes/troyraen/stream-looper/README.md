# Streaming Stream Looper

Set a startup script to execute the python file in a background thread:

```bash
startupscript="#! /bin/bash
dir=/home/consumer_sim/
fname=streaming_stream_looper
nohup python3 \${dir}\${fname}.py >> \${dir}\${fname}.out 2>&1 &
"

gcloud compute instances add-metadata stream-looper --metadata=startup-script="$startupscript"

gcloud compute instances start stream-looper
```

Run this in `screen` to debug

```python
from streaming_stream_looper import StreamLooper

TOPIC_NAME = "ztf-loop"
SUBSCRIPTION_NAME = "ztf-alerts-reservoir"
looper = StreamLooper(TOPIC_NAME, SUBSCRIPTION_NAME)
looper.run_looper()
```
