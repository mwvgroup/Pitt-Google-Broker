#! /bin/bash
# Configure and Start the Kafka -> Pub/Sub connector

workingdir=/home/broker/consumer
# mkdir -p ${workingdir} # keytab auth file must already exist in this dir
cd ${workingdir}

#--- Get project and instance metadata
# for info on working with metadata, see here
# https://cloud.google.com/compute/docs/storing-retrieving-metadata
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
zone=$(curl "${baseurl}/instance/zone" -H "${H}")
PS_TOPIC=$(curl "${baseurl}/instance/attributes/PS_TOPIC" -H "${H}")
KAFKA_TOPIC=$(curl "${baseurl}/instance/attributes/KAFKA_TOPIC" -H "${H}")

#--- Download config template files from GCS
for f in psconnect-worker.properties ps-connector.properties
do
    gsutil cp "gs://${PROJECT_ID}-broker_files/consumer/${f}" "${f}"
done

#--- Set project and topic configs using the instance metadata
fconfig=ps-connector.properties
sed -i "s/PROJECT_ID/${PROJECT_ID}/g" ${fconfig}
sed -i "s/PS_TOPIC/${PS_TOPIC}/g" ${fconfig}
sed -i "s/KAFKA_TOPIC/${KAFKA_TOPIC}/g" ${fconfig}

cd /bin

#--- Check until alerts start streaming into the topic
alerts_flowing=false
while [ "${alerts_flowing}" = false ]
do
    # get list of live topics and dump to file
    # /bin/kafka-topics works, but exits with:
        # TGT renewal thread has been interrupted and will exit.
        # (org.apache.kafka.common.security.kerberos.KerberosLogin)""
    # which kills the while loop. no working suggestions found online.
    # passing the error with `|| true`
    {
        /bin/kafka-topics \
            --bootstrap-server public2.alerts.ztf.uw.edu:9094 \
            --list \
            --command-config ${workingdir}/admin.properties \
            > list.topics
    } || {
        true
    }

    # check if our topic is in the list
    if grep -Fq "${KAFKA_TOPIC}" list.topics
    then
        alerts_flowing=true  # start consuming
    else
        # sleep 1 min, then try again
        sleep 60s
    fi
done

#--- Start the Kafka -> Pub/Sub connector
/bin/connect-standalone \
    ${workingdir}/psconnect-worker.properties \
    ${workingdir}/ps-connector.properties
