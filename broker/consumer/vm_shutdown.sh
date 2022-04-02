#! /bin/bash

# Get VM name
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
vm_name="$(curl ${baseurl}/instance/name -H ${H})"

# Unset metadata so there's no unexpected behvaior on startup
topics="KAFKA_TOPIC_FORCE=,PS_TOPIC=,PS_TOPIC_FORCE=,PS_TOPIC="
gcloud compute instances add-metadata "${vm_name}" --metadata="${topics}"
