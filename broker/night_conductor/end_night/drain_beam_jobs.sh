#! /bin/bash
# Stop/Drain the Dataflow jobs with job IDs in the RUNNING_BEAM_JOBS attribute
# (set in night_conductor/start_night/start_beam_jobs.sh)

region=us-central1
zone=us-central1-a
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"

# Drain the jobs
RUNNING_BEAM_JOBS=$(curl "${baseurl}/instance/attributes/RUNNING_BEAM_JOBS" -H "${H}")
gcloud dataflow jobs drain ${RUNNING_BEAM_JOBS} --region ${region}

# unset the RUNNING_BEAM_JOBS attribute
instancename=$(curl "${baseurl}/instance/name" -H "${H}")
gcloud compute instances add-metadata ${instancename} --zone=${zone} \
      --metadata RUNNING_BEAM_JOBS=""
