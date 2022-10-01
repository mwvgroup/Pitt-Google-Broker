#! /bin/bash

# Get VM name
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
vm_name=$(curl "${baseurl}/instance/name" -H "${H}")
zone=$(curl "${baseurl}/instance/zone" -H "${H}")

# clear the forced topics so there's no unexpected behvaior on next startup
topics="KAFKA_TOPIC_FORCE=,PS_TOPIC_FORCE="
gcloud compute instances add-metadata "${vm_name}" --zone "${zone}" --metadata="${topics}"

# these have no effect when set manually. delete them to avoid confusion.
topics="CURRENT_KAFKA_TOPIC,CURRENT_PS_TOPIC"
gcloud compute instances remove-metadata "${vm_name}" --zone "${zone}" --keys="${topics}"
