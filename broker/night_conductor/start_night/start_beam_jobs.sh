#! /bin/bash
# Starts the Beam/Dataflow job(s) and waits for status = RUNNING

PROJECT_ID=$1
brokerdir=$2
bucket=$3
cd ${brokerdir}

# copy the broker's Beam directory from GCS and cd in
gsutil cp -r gs://${bucket}/beam .
cd beam
beamdir=$(pwd)

# copy beam_helpers modules to job dirs
mkdir -p ztf_bq_sink/beam_helpers
cp beam_helpers/__init__.py beam_helpers/data_utils.py ztf_bq_sink/beam_helpers/.
cp -r beam_helpers ztf_value_added/.

# set configs
source jobs.config ${PROJECT_ID} ${beamdir}

# start the ztf-value_added job
# the command holds the terminal, so use timeout.
# this does _not_ cancel the dataflow job.
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
        --streaming
# If we can get the previous command to return the job info
# like it's "supposed" to
# instead of holding the terminal,
# we should be able to parse out the job ID and then
# get the job status this way:
# gcloud dataflow jobs list --project=<PROJECT_ID> --filter="id=<JOB_ID>" --format="get(state)"
# Then check every N(=30?) seconds until the job is "RUNNING" or "FAILED".
#
# We should also store the job ID in a file in the GCS ${bucket}
# so the conductor can use it later to stop the job.

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
        --streaming
