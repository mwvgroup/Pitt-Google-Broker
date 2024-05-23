# Start the Rubin consumer VM

See `Pitt-Google-Broker/broker/setup_broker/rubin/README.md` for setup instructions.

To start the consumer VM:

```bash
survey="rubin"
testid="mytest"
consumerVM="${survey}-consumer-${testid}"
zone="us-central1-a"

# Set the VM metadata
KAFKA_TOPIC="alerts-simulated"
PS_TOPIC="${survey}-alerts-${testid}"
gcloud compute instances add-metadata "${consumerVM}" --zone "${zone}" \
    --metadata="PS_TOPIC_FORCE=${PS_TOPIC},KAFKA_TOPIC_FORCE=${KAFKA_TOPIC}"

# Start the VM
gcloud compute instances start ${consumerVM} --zone ${zone}
# this launches the startup script which configures and starts the
# Kafka -> Pub/Sub connector
```

To stop stop the consumer VM:

```bash
survey="rubin"
testid="mytest"
consumerVM="${survey}-consumer-${testid}"
zone="us-central1-a"

# Stop the VM
gcloud compute instances stop ${consumerVM} --zone ${zone}
```