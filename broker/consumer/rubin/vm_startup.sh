#! /bin/bash
# Configure and Start the Kafka -> Pub/Sub connector

brokerdir=/home/broker

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

#--- Download config files from GCS
# remove all files
rm -r "${brokerdir}"
# download fresh files
mkdir "${brokerdir}"
cd ${brokerdir} || exit
gsutil -m cp -r "gs://${broker_bucket}/consumer" .
# wait. otherwise the script may continue before all files are downloaded, with adverse behavior.
sleep 30s

#--- Set the topic names to the "FORCE" metadata attributes if exist, else defaults
KAFKA_TOPIC_DEFAULT="alerts-simulated"
KAFKA_TOPIC="${KAFKA_TOPIC_FORCE:-${KAFKA_TOPIC_DEFAULT}}"
PS_TOPIC="${PS_TOPIC_FORCE:-${PS_TOPIC_DEFAULT}}"
# set VM metadata, just for clarity and easy viewing
gcloud compute instances add-metadata "$consumerVM" --zone "$zone" \
    --metadata="PS_TOPIC=${PS_TOPIC},KAFKA_TOPIC=${KAFKA_TOPIC}"

#--- Files this script will write
workingdir="${brokerdir}/consumer/${survey}"
fout_run="${workingdir}/run-connector.out"
fout_topics="${workingdir}/list.topics"

#--- Set the connector's configs (Kafka username and password, project, and topics)
# define Rubin-related parameters
#kafka_username="${survey}-${PROJECT_ID}-kafka-username"
kafka_password="${survey}-${PROJECT_ID}-kafka-password"
#KAFKA_USERNAME=$(gcloud secrets versions access latest --secret="${kafka_username}")
KAFKA_PASSWORD=$(gcloud secrets versions access latest --secret="${kafka_password}")

cd "${workingdir}" || exit

fconfig=admin.properties
#sed -i "s/KAFKA_USERNAME/${KAFKA_USERNAME}/g" ${fconfig}
sed -i "s/KAFKA_PASSWORD/${KAFKA_PASSWORD}/g" ${fconfig}

fconfig=psconnect-worker.properties
#sed -i "s/KAFKA_USERNAME/${KAFKA_USERNAME}/g" ${fconfig}
sed -i "s/KAFKA_PASSWORD/${KAFKA_PASSWORD}/g" ${fconfig}

fconfig=ps-connector.properties
sed -i "s/PROJECT_ID/${PROJECT_ID}/g" ${fconfig}
sed -i "s/PS_TOPIC/${PS_TOPIC}/g" ${fconfig}
sed -i "s/KAFKA_TOPIC/${KAFKA_TOPIC}/g" ${fconfig}

#--- Check until alerts start streaming into the topic
alerts_flowing=false
while [ "${alerts_flowing}" = false ]
do
    # get list of topics and dump to file
    /bin/kafka-topics \
        --bootstrap-server usdf-alert-stream-dev.lsst.cloud:9094 \
        --list \
        --command-config "${workingdir}/admin.properties" \
        > "${fout_topics}"

    # check if our topic is in the list
    if grep -Fq "${KAFKA_TOPIC}" "${fout_topics}"
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
    &>> "${fout_run}"
