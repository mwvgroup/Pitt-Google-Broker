#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

testid="${1:-test}"
# "False" uses production resources
# any other string will be appended to the names of all resources
teardown="${2:-False}"
# "True" tearsdown/deletes resources, else setup
survey="${3:-lsst}"
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

# function used to define GCP resources; appends testid if needed
define_GCP_resources() {
    local base_name="$1"
    local testid_suffix=""

    if [ "$testid" != "False" ]; then
        if [ "$base_name" = "$survey" ]; then
            testid_suffix="_${testid}"  # complies with BigQuery naming conventions
        else
            testid_suffix="-${testid}"
        fi
    fi

    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used directly in this script
broker_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}-broker_files")
topic_alerts=$(define_GCP_resources "${survey}-alerts")
pubsub_subscription=$(define_GCP_resources "${topic_alerts}")

# function used to create (or delete) GCP resources
manage_resources() {
    local mode="$1"  # setup or teardown
    local environment_type="production"

    if [ "$testid" != "False" ]; then
        environment_type="testing"
    fi

    if [ "$mode" = "setup" ]; then
        # setup resources
        echo
        echo "Creating broker_bucket and uploading files..."
        gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
        ./upload_broker_bucket.sh "${broker_bucket}"

        # create Pub/Sub
        echo
        echo "Configuring Pub/Sub resources..."
        gcloud pubsub topics create "${topic_alerts}"
        gcloud pubsub subscriptions create "${pubsub_subscription}" --topic="${topic_alerts}"

        # set IAM policies on resources
        user="allUsers"
        roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
        gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"
    else
        if [ "$environment_type" = "testing" ]; then
            o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
            gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
            gcloud pubsub topics delete "${topic_alerts}"
            gcloud pubsub subscriptions delete "${pubsub_subscription}"
        fi
    fi
}

#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "$teardown" = "True" ]; then
    manage_resources "teardown"
else
    manage_resources "setup"
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
./create_vm.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}" "${firewallrule}"
