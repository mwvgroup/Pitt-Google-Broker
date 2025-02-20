#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-lsst}"
schema_version="${4:-7.3}"
versiontag=v$(echo "${schema_version}" | tr . _) # 7.3 -> v7_3
region="${5:-us-central1}"
zone="${region}-a"  # just use zone "a" instead of adding another script arg

PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable

#--- Make the user confirm the settings
echo
echo "setup_broker.sh will run with the following configs: "
echo
echo "GOOGLE_CLOUD_PROJECT = ${PROJECT_ID}"
echo "survey = ${survey}"
echo "testid = ${testid}"
echo "schema_version = ${schema_version}"
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
topic_alerts_raw=$(define_GCP_resources "${survey}-alerts_raw")
topic_alerts=$(define_GCP_resources "${survey}-alerts")
subscription_reservoir=$(define_GCP_resources "${survey}-alerts-reservoir")

# function used to create (or delete) GCP resources
manage_resources() {
    local mode="$1"  # setup or teardown
    local environment_type="production"

    if [ "$testid" != "False" ]; then
        environment_type="testing"
    fi

    if [ "$mode" = "setup" ]; then
        # create broker bucket and upload files
        echo
        echo "Creating broker_bucket and uploading files..."
        gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
        ./upload_broker_bucket.sh "${broker_bucket}"

        # create a firewall rule to open the port used by Kafka/Rubin LSST
        # on any instance with the flag --tags=tcpport9094
        echo
        echo "Configuring Rubin/Kafka firewall rule..."
        firewallrule="tcpport9094"
        gcloud compute firewall-rules create "${firewallrule}" \
            --allow=tcp:9094 \
            --description="Allow incoming traffic on TCP port 9094" \
            --direction=INGRESS \
            --enable-logging

        # create Pub/Sub
        echo "Configuring Pub/Sub resources..."
        gcloud pubsub topics create "${topic_alerts_raw}"
        gcloud pubsub topics create "${topic_alerts}"
        gcloud pubsub subscriptions create "${subscription_reservoir}" --topic="${topic_alerts}"

        # set IAM policies on resources
        user="allUsers"
        roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
        gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"
    else
        if [ "$environment_type" = "testing" ]; then
            o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
            gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
            gcloud pubsub topics delete "${topic_alerts_raw}"
            gcloud pubsub topics delete "${topic_alerts}"
            gcloud pubsub subscriptions delete "${subscription_reservoir}"
        else
            echo 'ERROR: No testid supplied.'
            echo 'To avoid accidents, this script will not delete production resources.'
            echo 'If that is your intention, you must delete them manually.'
            echo 'Otherwise, please supply a testid.'
            exit 1
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

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vm.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}" "${firewallrule}"

#--- Deploy Cloud Functions
echo
echo "Configuring Cloud Functions..."
cd .. && cd .. || exit
cd cloud_functions && cd lsst || exit

#--- Pub/Sub -> Cloud Storage Avro cloud function
cd ps_to_gcs || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag" "$region"

#--- return to setup_broker directory
cd .. && cd .. || exit
cd .. && cd setup_broker || exit
