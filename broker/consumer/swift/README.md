# Start the Swift/BAT-GUANO consumer VM

See `broker/setup_broker/swift/README.md` for setup instructions.

To start the consumer VM:

```bash
survey="swift"
testid="mytest"
consumerVM="${survey}-consumer-${testid}"
zone="us-central1-a"

# Set the VM metadata
KAFKA_TOPIC="enter Kafka topic"
PS_TOPIC="${survey}-alerts-${testid}"
gcloud compute instances add-metadata ${consumerVM} --zone=${zone} \
      --metadata KAFKA_TOPIC=${KAFKA_TOPIC},PS_TOPIC=${PS_TOPIC}

# Start the VM
gcloud compute instances start ${consumerVM} --zone ${zone}
# this launches the startup script which configures and starts the
# Kafka -> Pub/Sub connector
```

To stop stop the consumer VM:

```bash
survey="swift"
testid="mytest"
consumerVM="${survey}-consumer-${testid}"
zone="us-central1-a"

# Stop the VM
gcloud compute instances stop ${consumerVM} --zone ${zone}
```
