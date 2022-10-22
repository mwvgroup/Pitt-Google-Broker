#! /bin/bash
# One-time setup for a GCP project

survey="${1:-elasticc}"

region="${CLOUDSDK_COMPUTE_REGION:-us-central1}"

#--- Create a firewall rule to open the port used by Kafka
# Implement this rule on a VM instance using the flag --tags=kafkaport
    echo
    echo "Opening port 9094 for Kafka..."
    gcloud compute firewall-rules create 'kafkaport' \
        --allow=tcp:9094 \
        --description="Allow incoming traffic on TCP port 9094" \
        --direction=INGRESS \
        --enable-logging

# Create an IAM role for a public user.
# this will be used later to grant permissions on specific resources
role_id="userPublic"
role_yaml="role_user_public.yml"
gcloud iam roles create "${role_id}" --project="${GOOGLE_CLOUD_PROJECT}" --file="${role_yaml}"

# Create a schedule for the Consumer VM
consumerVMsched="${survey}-consumer-schedule"
start_schedule='45 19 * * *'  # 19:45 UTC / 12:45pm PDT, everyday
stop_schedule='00 00 * * *'  # 00:00 UTC / 5:00pm PDT, everyday
gcloud compute resource-policies create instance-schedule "${consumerVMsched}" \
    --description="Start Consumer each night, stop each morning." \
    --region="${region}" \
    --vm-start-schedule="${start_schedule}" \
    --vm-stop-schedule="${stop_schedule}" \
    --timezone="UTC"
