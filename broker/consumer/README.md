See [`kafka_console_connect.md`](kafka_console_connect.md)

To start the `ztf-consumer` VM and begin ingesting a ZTF topic:

```bash
survey="ztf"
testid="mytest"
instancename="${survey}-consumer-${testid}"
zone=us-central1-a

# Set the VM metadata
KAFKA_TOPIC=ztf_20210120_programid1 # ztf_yyyymmdd_programid1
# must be within the last 7 days and contain at least 1 alert
PS_TOPIC="ztf_alerts-${testid}"
gcloud compute instances add-metadata ${instancename} --zone=${zone} \
      --metadata KAFKA_TOPIC=${KAFKA_TOPIC},PS_TOPIC=${PS_TOPIC}

# Start the VM
gcloud compute instances start ${instancename} --zone ${zone}
# this launches the startup script which configures and starts the
# Kafka -> Pub/Sub connector
```
