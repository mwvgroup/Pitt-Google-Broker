#! /bin/bash
# Configure and Start the Kafka -> Pub/Sub connector

brokerdir=/home/broker
# if using an authenticated connection, the keytab file must already exist in the workingdir
workingdir="${brokerdir}/consumer"

#--- Get project and instance metadata
# for info on working with metadata, see here
# https://cloud.google.com/compute/docs/storing-retrieving-metadata
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
zone=$(curl "${baseurl}/instance/zone" -H "${H}")
PS_TOPIC_FORCE=$(curl "${baseurl}/instance/attributes/PS_TOPIC_FORCE" -H "${H}")
KAFKA_TOPIC_FORCE=$(curl "${baseurl}/instance/attributes/KAFKA_TOPIC_FORCE" -H "${H}")
USE_AUTHENTICATION=$(curl "${baseurl}/instance/attributes/USE_AUTHENTICATION" -H "${H}")
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
cd ${brokerdir}
gsutil -m cp -r "gs://${broker_bucket}/consumer" .
gsutil -m cp -r "gs://${broker_bucket}/schema_maps" .
# wait. otherwise the script may continue before all files are downloaded, with adverse behavior.
sleep 30s
cd ${workingdir}

#--- Set the topic names to the "FORCE" metadata attributes if exist, else defaults
kafka_topic_syntax=$(cat "${brokerdir}/schema_maps/${survey}.yaml" | yq ".TOPIC_SYNTAX")
yyyymmdd=$(date -u '+%Y%m%d')
KAFKA_TOPIC_DEFAULT="${kafka_topic_syntax/yyyymmdd/${yyyymmdd}}"
KAFKA_TOPIC="${KAFKA_TOPIC_FORCE:-${KAFKA_TOPIC_DEFAULT}}"
PS_TOPIC="${PS_TOPIC_FORCE:-${PS_TOPIC_DEFAULT}}"
# set VM metadata, just for clarity and easy viewing
gcloud compute instances add-metadata "$consumerVM" --zone "$zone" \
    --metadata="PS_TOPIC=${PS_TOPIC},KAFKA_TOPIC=${KAFKA_TOPIC}"


#--- Files this script will write
fout_run="${workingdir}/run-connector.out"
fout_topics="${workingdir}/list.topics"

#--- Set the connector's configs (client ID and client secret) for LIGO/Virgo/KAGRA (LVK)
if [ "$survey" == "lvk" ]; then
    # define LVK-related parameters
    bootstrap_server="kafka.gcn.nasa.gov:9092"
    surveydir="${workingdir}/lvk"
    CLIENT_ID=$(gcloud secrets versions access latest --secret=lvk-pitt-google-broker-testing-client-id)
    CLIENT_SECRET=$(gcloud secrets versions access latest --secret=lvk-pitt-google-broker-testing-client-secret)
    
    cd ${surveydir} || exit

    fconfig=admin.properties
    sed -i "s/CLIENT_ID/${CLIENT_ID}/g" ${fconfig}
    sed -i "s/CLIENT_SECRET/${CLIENT_SECRET}/g" ${fconfig}

    fconfig=psconnect-worker-authenticated.properties
    sed -i "s/CLIENT_ID/${CLIENT_ID}/g" ${fconfig}
    sed -i "s/CLIENT_SECRET/${CLIENT_SECRET}/g" ${fconfig}

else
    # define ZTF-related parameters
    if [ "${USE_AUTHENTICATION}" = true ]; then
        bootstrap_server="public2.alerts.ztf.uw.edu:9094"
    else
        bootstrap_server="public2.alerts.ztf.uw.edu:9092"
    fi
    surveydir="${workingdir}" 
fi

#--- Set the connector's configs (project and topics)
fconfig=ps-connector.properties
sed -i "s/PROJECT_ID/${PROJECT_ID}/g" ${fconfig}
sed -i "s/PS_TOPIC/${PS_TOPIC}/g" ${fconfig}
sed -i "s/KAFKA_TOPIC/${KAFKA_TOPIC}/g" ${fconfig}

#--- Check until alerts start streaming into the topic
alerts_flowing=false
while [ "${alerts_flowing}" = false ]
do
    # get list of topics and dump to file
    # /bin/kafka-topics works, but exits with:
        # TGT renewal thread has been interrupted and will exit.
        # (org.apache.kafka.common.security.kerberos.KerberosLogin)""
    # which kills the while loop. no working suggestions found.
    # passing the error with `|| true`
    if [ "${USE_AUTHENTICATION}" = true ]
    then
        {
            /bin/kafka-topics \
                --bootstrap-server ${bootstrap_server} \
                --list \
                --command-config ${surveydir}/admin.properties \
                > ${fout_topics}
        } || {
            true
        }
    else
        {
            /bin/kafka-topics \
                --bootstrap-server ${bootstrap_server} \
                --list \
                > ${fout_topics}
        } || {
            true
        }
    fi

    # check if our topic is in the list
    if grep -Fq "${KAFKA_TOPIC}" $fout_topics
    then
        alerts_flowing=true  # start consuming
    else
        sleep 60s  # sleep 1 min, then try again
    fi
done

#--- Start the Kafka -> Pub/Sub connector, save stdout and stderr to file
if [ "${USE_AUTHENTICATION}" = true ]
then
    /bin/connect-standalone \
        ${surveydir}/psconnect-worker-authenticated.properties \
        ${surveydir}/ps-connector.properties \
        &>> ${fout_run}
else
    /bin/connect-standalone \
        ${surveydir}/psconnect-worker-unauthenticated.properties \
        ${surveydir}/ps-connector.properties \
        &>> ${fout_run}
fi
