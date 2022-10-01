#! /bin/bash

# Get VM name
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
vm_name=$(curl "${baseurl}/instance/name" -H "${H}")

# Unset FORCE topics in metadata so there's no unexpected behvaior on next startup
topics="KAFKA_TOPIC_FORCE=,PS_TOPIC_FORCE="
gcloud compute instances add-metadata "${vm_name}" --metadata="${topics}"
