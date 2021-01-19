#! /bin/bash
# Starts the Beam/Dataflow job(s)

PROJECT_ID=$1
brokerdir=$2
bucket=$3
cd ${brokerdir}

# Copy the broker's Beam directory from GCS and cd in
gsutil -m cp -r gs://${bucket}/beam .
cd beam
beamdir=$(pwd)

# Copy beam_helpers modules to job dirs so setup.py works correctly
mkdir -p ztf_bq_sink/beam_helpers
cp beam_helpers/__init__.py beam_helpers/data_utils.py ztf_bq_sink/beam_helpers/.
cp -r beam_helpers ztf_value_added/.

# Set configs
source jobs.config ${PROJECT_ID} ${beamdir}

# Start the ztf-value_added job.
# - the command holds the terminal, so use timeout (does not cancel the job).
# - send the output to a file.
cd ztf_value_added
timeout 30 \
    python3 beam_ztf_value_added.py \
        --experiments use_runner_v2 \
        --setup_file ${setup_file_valadd} \
        --runner ${runner} \
        --region ${region} \
        --project ${PROJECT_ID} \
        --job_name ${dataflow_job_name_valadd} \
        --max_num_workers ${max_num_workers_valadd} \
        --staging_location ${staging_location} \
        --temp_location ${temp_location} \
        --PROJECTID ${PROJECT_ID} \
        --source_PS_ztf ${source_PS_ztf} \
        --sink_BQ_salt2 ${sink_BQ_salt2} \
        --sink_PS_exgalTrans ${sink_PS_exgalTrans} \
        --sink_PS_salt2 ${sink_PS_salt2} \
        --streaming \
    &> runjob.out
# get the Job id so we can use it to stop the job later
jobid1=$(grep "Submitted job:" runjob.out | awk '{print $(NF)}')

# Start the ztf -> BQ job
cd ${beamdir} && cd ztf_bq_sink
timeout 30 \
    python3 beam_ztf_bq_sink.py \
        --experiments use_runner_v2 \
        --setup_file ${setup_file_bqsink} \
        --runner ${runner} \
        --region ${region} \
        --project ${PROJECT_ID} \
        --job_name ${dataflow_job_name_bqsink} \
        --max_num_workers ${max_num_workers_bqsink} \
        --staging_location ${staging_location} \
        --temp_location ${temp_location} \
        --PROJECTID ${PROJECT_ID} \
        --source_PS_ztf ${source_PS_ztf} \
        --sink_BQ_originalAlert ${sink_BQ_originalAlert} \
        --streaming \
    &> runjob.out
# get the Job id so we can use it to stop the job later
jobid2=$(grep "Submitted job:" runjob.out | awk '{print $(NF)}')

# collect job ids
RUNNING_BEAM_JOBS="${jobid1} ${jobid2}"

# Set RUNNING_BEAM_JOBS as metadata
# - this will be used in end_night.sh to stop (drain) the jobs
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
instancename=$(curl "${baseurl}/instance/name" -H "${H}")
zone=us-central1-a
gcloud compute instances add-metadata ${instancename} --zone=${zone} \
      --metadata RUNNING_BEAM_JOBS="${RUNNING_BEAM_JOBS}"

# Make sure the jobs are running
for jobid in "${RUNNING_BEAM_JOBS}"
do
    jobstate=""
    while [ "${jobstate}" != "Running" ]
    do
        jobstate=$(gcloud dataflow jobs list --project="${PROJECT_ID}" --filter="id=${jobid}" --format="get(state)")
        # if it's not running, wait before checking again
        if [ "${jobstate}" != "Running" ]
        then
            sleep 30s
        fi
    done
done
