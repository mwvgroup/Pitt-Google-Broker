#! /bin/bash
# Stop/Drain the Dataflow jobs with job IDs in the RUNNING_BEAM_JOBS attribute
# (set in night_conductor/start_night/start_beam_jobs.sh)

PROJECT_ID=$1

region=us-central1
zone=us-central1-a
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"

# Drain the jobs
RUNNING_BEAM_JOBS=$(curl "${baseurl}/instance/attributes/RUNNING_BEAM_JOBS" -H "${H}")
gcloud dataflow jobs drain ${RUNNING_BEAM_JOBS} --region ${region}

# Wait until the draining finishes (or the jobs get cancelled manually)
for jobid in $RUNNING_BEAM_JOBS
do
    jobstate=""
    while [ "${jobstate}" != "Drained" ] && [ "${jobstate}" != "Cancelled" ]
    do
        jobstate=$(gcloud dataflow jobs list --project="${PROJECT_ID}" --filter="id=${jobid}" --format="get(state)")

        echo "jobid = ${jobid}"
        echo "jobstate = ${jobstate}"

        # if it's not drained, wait before checking again
        if [ "${jobstate}" != "Drained" ] && [ "${jobstate}" != "Cancelled" ]
        then
            sleep 30s
        fi
    done
done


# unset the RUNNING_BEAM_JOBS attribute
instancename=$(curl "${baseurl}/instance/name" -H "${H}")
gcloud compute instances add-metadata ${instancename} --zone=${zone} \
      --metadata RUNNING_BEAM_JOBS=""
