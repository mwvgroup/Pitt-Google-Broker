#! /bin/bash
#
# Create and configure GCP resources needed to run the nightly broker.
#
# To set up resources for _production_ broker instance, use
#   testid=False
#
# To setup resources for a _testing_ broker instance tagged with "mytest", use
#   testid=mytest
# The testid may contain only lowercase letters and numbers
# and must begin with a letter.
# The testid will be appended to the names of all resources.
#
# To delete resources associated with a _testing_ instance tagged with "mytest", use
#   testid=mytest
#   teardown=True
#


testid="${1:-test}"
# "False" uses production resources
# any other string will be appended to the names of all resources
teardown="${2:-False}"
# "True" tearsdown/deletes resources, else setup
survey="${3:-ztf}"
# name of the survey this broker instance will ingest
# 'ztf' or 'decat'
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
echo "Continue?  [y/N]: "

read continue_with_setup
continue_with_setup="${continue_with_setup:-N}"
if [ "$continue_with_setup" != "y" ]; then
    echo "Exiting setup."
    echo
    exit
fi

#--- GCP resources used directly in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
avro_bucket="${PROJECT_ID}-${survey}-alert_avros"
avro_topic="projects/${PROJECT_ID}/topics/${survey}-alert_avros"
# use test resources, if requested
# (there must be a better way to do this)
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
    avro_bucket="${avro_bucket}-${testid}"
    avro_topic="${avro_topic}-${testid}"
fi

#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "$testid" != "False" ]; then
    if [ "$teardown" = "True" ]; then
        # delete testing resources
        python3 setup_gcp.py --survey="$survey" --testid="$testid" --teardown
    else
        # setup testing resources
        python3 setup_gcp.py --survey="$survey" --testid="$testid"
        # ./create_bq_tables.sh "$PROJECT_ID" "$testid"
    fi
else
    # setup production resources
    python3 setup_gcp.py --survey="$survey" --production
fi

if [ "$teardown" != "True" ]; then

    #--- Upload some broker files to GCS so the VMs can use them
    echo
    echo "Uploading broker files to GCS..."
    o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
    gsutil -m -o "$o" cp -r ../beam "gs://${broker_bucket}"
    gsutil -m -o "$o" cp -r ../consumer "gs://${broker_bucket}"
    gsutil -m -o "$o" cp -r ../night_conductor "gs://${broker_bucket}"
    gsutil -m -o "$o" cp -r ../broker_utils/schema_maps "gs://${broker_bucket}"

    #--- Setup the Pub/Sub notifications on ZTF Avro storage bucket
    echo
    echo "Configuring Pub/Sub notifications on GCS bucket..."
    format=none  # json or none; whether to deliver the payload with the PS msg
    gsutil notification create \
                -t "$avro_topic" \
                -e OBJECT_FINALIZE \
                -f "$format" \
                "gs://${avro_bucket}"

    #--- Create a firewall rule to open the port used by Kafka/ZTF
    # on any instance with the flag --tags=ztfport
    echo
    echo "Configuring ZTF/Kafka firewall rule..."
    gcloud compute firewall-rules create 'ztfport' \
        --allow=tcp:9094 \
        --description="Allow incoming traffic on TCP port 9094" \
        --direction=INGRESS \
        --enable-logging

fi

#--- Deploy Cloud Functions
echo
echo "Configuring Cloud Functions..."
./deploy_cloud_fncs.sh "$testid" "$teardown" "$survey"

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "$broker_bucket" "$testid" "$teardown" "$survey"
# takes about 5 min to complete; waits for VMs to start up
