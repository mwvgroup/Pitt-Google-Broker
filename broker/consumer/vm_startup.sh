#! /bin/bash
# Configure and Start the Kafka -> Pub/Sub connector

brokerdir=/home/broker
workingdir="${brokerdir}/consumer"
# mkdir -p ${workingdir} # keytab auth file must already exist in this dir

#--- Get project and instance metadata
# for info on working with metadata, see here
# https://cloud.google.com/compute/docs/storing-retrieving-metadata
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
PS_TOPIC=$(curl "${baseurl}/instance/attributes/PS_TOPIC" -H "${H}")
KAFKA_TOPIC=$(curl "${baseurl}/instance/attributes/KAFKA_TOPIC" -H "${H}")
# parse the survey name and testid from the VM name
consumerVM=$(curl "${baseurl}/instance/name" -H "${H}")
survey=$(echo "$consumerVM" | awk -F "-" '{print $1}')
if [ "$consumerVM" = "${survey}-consumer" ]; then
    testid="False"
else
    testid=$(echo "$consumerVM" | awk -F "-" '{print $NF}')
fi

#--- GCP resources used in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
fi

#--- Files this script will write
fout_run="${workingdir}/run-connector.out"
fout_topics="${workingdir}/list.topics"

#--- Download config files from GCS (just grab the whole bucket)
cd "$brokerdir"
# remove all consumer files except the keytab
find "$workingdir" -type f -not -name 'pitt-reader.user.keytab' -delete
# download fresh files
gsutil -m cp -r "gs://${broker_bucket}/consumer" .

cd "$workingdir"

#--- Set project and topic configs using the instance metadata
fconfig=ps-connector.properties
sed -i "s/PROJECT_ID/${PROJECT_ID}/g" "$fconfig"
sed -i "s/PS_TOPIC/${PS_TOPIC}/g" "$fconfig"
sed -i "s/KAFKA_TOPIC/${KAFKA_TOPIC}/g" "$fconfig"

#--- Check until alerts start streaming into the topic
alerts_flowing=false
while [ "${alerts_flowing}" = false ]
do
    # get list of live topics and dump to file
    {
        /bin/kafka-topics \
            --bootstrap-server public2.alerts.ztf.uw.edu:9094 \
            --list \
            --command-config "${workingdir}/admin.properties" \
            > "$fout_topics"
    } || {
        true
    }
    # /bin/kafka-topics works, but exits with:
        # TGT renewal thread has been interrupted and will exit.
        # (org.apache.kafka.common.security.kerberos.KerberosLogin)""
    # which kills the while loop. no working suggestions found.
    # passing the error with `|| true`

    # check if our topic is in the list
    if grep -Fq "$KAFKA_TOPIC" "$fout_topics"
    then
        alerts_flowing=true  # start consuming
    else
        sleep 60s  # sleep 1 min, then try again
    fi
done

#--- Start the Kafka -> Pub/Sub connector, save stdout and stderr to file
/bin/connect-standalone \
    "${workingdir}/psconnect-worker.properties" \
    "${workingdir}/ps-connector.properties" \
    &>> "$fout_run"
