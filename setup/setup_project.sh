#! /bin/bash
# One-time setup for a GCP project

#--- Create a firewall rule to open the port used by Kafka
# Implement this rule on a VM instance using the flag --tags=kafkaport
    echo
    echo "Opening port 9094 for Kafka..."
    gcloud compute firewall-rules create 'kafkaport' \
        --allow=tcp:9094 \
        --description="Allow incoming traffic on TCP port 9094" \
        --direction=INGRESS \
        --enable-logging
