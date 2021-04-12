# Beam + Dataflow Data Processing Pipeline

See [`beam-dataflow-primer.md`](beam_dataflow_primer.md) for intros to Beam and Dataflow.
It is interspersed with references to components of the pipeline(s) that we deploy here.

To manually start the jobs (defined in
[`ztf_value_added/beam_ztf_value_added.py`](ztf_value_added/beam_ztf_value_added.py)
and [`ztf_bq_sink/beam_ztf_bq_sink.py`](ztf_bq_sink/beam_ztf_bq_sink.py)):

1. Clone this repo.

2. Set up your environment (a Conda env is recommended). Either:
    - Fresh/full install: Install the broker package + dependencies following [https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html](https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html) (Complete sections "Installing the package" and "Defining Environmental Variables")
    - Install Beam and GCP dependencies on top of existing broker install: `pip install apache-beam[gcp]`

3. `cd` to this directory (`broker/beam`)

4. Set configs and start the jobs:

```bash
#-- Set configs
PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
testid=mytest # see broker/README.md to setup testing resources
beamdir=$(pwd)
source jobs.config ${PROJECT_ID} ${testid} ${beamdir}

#-- Copy beam_helpers modules.
# Modules in the beam_helpers directory are used by multiple jobs.
# They need to be copied into the jobs' directories so setup.py can find them.
mkdir -p ztf_bq_sink/beam_helpers
cp beam_helpers/__init__.py beam_helpers/data_utils.py ztf_bq_sink/beam_helpers/.
cp -r beam_helpers ztf_value_added/.

#-- Start the ztf value-added processing Dataflow job
cd ztf_value_added
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
            --sink_CS_salt2 ${sink_CS_salt2} \
            --sink_PS_pure ${sink_PS_pure} \
            --sink_PS_exgalTrans ${sink_PS_exgalTrans} \
            --sink_PS_salt2 ${sink_PS_salt2} \
            --salt2_SNthresh ${salt2_SNthresh} \
            --salt2_minNdetections ${salt2_minNdetections} \
            --streaming \
            --update  # use if updating a currently running job; job_name must match current job
# Use “Ctrl + C” to regain control of the terminal.
# this will _not_ cancel the job

# Start the ztf -> BQ job
cd ${beamdir} && cd ztf_bq_sink
python beam_ztf_bq_sink.py \
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
            --sink_BQ_diasource ${sink_BQ_diasource} \
            --streaming \
            --update  # use if updating a currently running job
# Use “Ctrl + C” to regain control of the terminal.
# this will _not_ cancel the job
cd ${beamdir}
```

5. View the [Dataflow job(s) in the GCP Console](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
