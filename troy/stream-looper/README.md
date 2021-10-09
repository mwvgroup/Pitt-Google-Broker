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
