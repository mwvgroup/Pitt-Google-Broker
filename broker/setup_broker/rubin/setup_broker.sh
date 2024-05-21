#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

testid="${1:-test}"
# "False" uses production resources
# any other string will be appended to the names of all resources
teardown="${2:-False}"
# "True" tearsdown/deletes resources, else setup
survey="${3:-rubin}"
# name of the survey this broker instance will ingest
region="${4:-us-central1}"
zone="${region}-a"  # just use zone "a" instead of adding another script arg

PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable

#--- Make the user confirm the settings
echo
echo "setup_broker.sh will run with the following configs: "
echo
echo "GOOGLE_CLOUD_PROJECT = ${PROJECT_ID}"
echo "survey = ${survey}"
echo "testid = ${testid}"
echo "teardown = ${teardown}"
echo
echo "Continue?  [y/(n)]: "

read -r continue_with_setup
continue_with_setup="${continue_with_setup:-n}"
if [ "$continue_with_setup" != "y" ]; then
    echo "Exiting setup."
    echo
    exit
fi

#--- GCP resources used directly in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
topic_alerts="${survey}-alerts"
pubsub_subscription="${topic_alerts}"
# use test resources, if requested
# (there must be a better way to do this)
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
    topic_alerts="${topic_alerts}-${testid}"
    pubsub_subscription="${pubsub_subscription}-${testid}"
fi


#--- Create (or delete) GCS, Pub/Sub resources
if [ "${teardown}" != "True" ]; then
    # create broker bucket and upload files
    echo "Creating broker_bucket and uploading files..."
    gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"

    # create pubsub
    echo "Configuring Pub/Sub resources..."
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub subscriptions create "${pubsub_subscription}" --topic="${topic_alerts}"

    # Set IAM policies on resources
    user="allUsers"
    roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
    gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"

else
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
        gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
        gcloud pubsub topics delete "${topic_alerts}"
        gcloud pubsub subscriptions delete "${pubsub_subscription}"
    fi
fi

if [ "$teardown" != "True" ]; then
    #--- Create a firewall rule to open the port used by Kafka/Rubin
    # on any instance with the flag --tags=tcpport9094
    echo
    echo "Configuring Rubin/Kafka firewall rule..."
    firewallrule="tcpport9094"
    gcloud compute firewall-rules create "${firewallrule}" \
        --allow=tcp:9094 \
        --description="Allow incoming traffic on TCP port 9094" \
        --direction=INGRESS \
        --enable-logging
fi

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}" "${firewallrule}"
