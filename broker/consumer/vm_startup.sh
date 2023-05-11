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
zone=$(curl "${baseurl}/instance/zone" -H "${H}")
PS_TOPIC_FORCE=$(curl "${baseurl}/instance/attributes/PS_TOPIC_FORCE" -H "${H}")
KAFKA_TOPIC_FORCE=$(curl "${baseurl}/instance/attributes/KAFKA_TOPIC_FORCE" -H "${H}")
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
PS_TOPIC_DEFAULT="${survey}-alerts_raw"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
    PS_TOPIC_DEFAULT="${PS_TOPIC_DEFAULT}-${testid}"
fi
# default Kafka topic
kafka_topic_syntax=$(cat "${brokerdir}/schema_maps/${survey}.yaml" | yq ".TOPIC_SYNTAX")
yyyymmdd=$(date -u '+%Y%m%d')
KAFKA_TOPIC_DEFAULT="${kafka_topic_syntax/yyyymmdd/${yyyymmdd}}"

#--- Set the topic names to the "FORCE" metadata attributes if exist, else defaults
KAFKA_TOPIC="${KAFKA_TOPIC_FORCE:-${KAFKA_TOPIC_DEFAULT}}"
PS_TOPIC="${PS_TOPIC_FORCE:-${PS_TOPIC_DEFAULT}}"
# set VM metadata, just for clarity and easy viewing
gcloud compute instances add-metadata "$consumerVM" --zone "$zone" \
    --metadata="PS_TOPIC=${PS_TOPIC},KAFKA_TOPIC=${KAFKA_TOPIC}"


#--- Files this script will write
fout_run="${workingdir}/run-connector.out"
fout_topics="${workingdir}/list.topics"

#--- Download config files from GCS (just grab the whole bucket)
cd ${brokerdir}
# remove all consumer files except the keytab
find ${workingdir} -type f -not -name 'pitt-reader.user.keytab' -delete
# download fresh files
gsutil -m cp -r "gs://${broker_bucket}/consumer" .
gsutil -m cp -r "gs://${broker_bucket}/schema_maps" .

cd ${workingdir}

#--- Set the connector's configs (project and topics)
fconfig=ps-connector.properties
sed -i "s/PROJECT_ID/${PROJECT_ID}/g" ${fconfig}
sed -i "s/PS_TOPIC/${PS_TOPIC}/g" ${fconfig}
sed -i "s/KAFKA_TOPIC/${KAFKA_TOPIC}/g" ${fconfig}

#--- Check until alerts start streaming into the topic
alerts_flowing=false
while [ "${alerts_flowing}" = false ]
do
    # get list of live topics and dump to file
    {
        /bin/kafka-topics \
            --bootstrap-server public.alerts.ztf.uw.edu:9092 \
            --list \
            --command-config ${workingdir}/admin.properties \
            > $fout_topics
    } || {
        true
    }
    # /bin/kafka-topics works, but exits with:
        # TGT renewal thread has been interrupted and will exit.
        # (org.apache.kafka.common.security.kerberos.KerberosLogin)""
    # which kills the while loop. no working suggestions found.
    # passing the error with `|| true`

    # check if our topic is in the list
    if grep -Fq "${KAFKA_TOPIC}" $fout_topics
    then
        alerts_flowing=true  # start consuming
    else
        sleep 60s  # sleep 1 min, then try again
    fi
done

#--- Start the Kafka -> Pub/Sub connector, save stdout and stderr to file
/bin/connect-standalone \
    ${workingdir}/psconnect-worker.properties \
    ${workingdir}/ps-connector.properties \
    &>> ${fout_run}
