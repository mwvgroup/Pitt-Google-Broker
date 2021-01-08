# Beam + Dataflow Data Processing Pipeline

See [`beam-dataflow-primer.md`](beam_dataflow_primer.md) for intros to Beam and Dataflow.
It is interspersed with references to components of the pipeline that we deploy here.

To start the job (which is defined in [`ztf_value_added/beam_ztf_value_added`](ztf_value_added/beam_ztf_value_added.py)):

1. Clone this repo.

2. Set up your environment (a Conda env is recommended). Either:
    - Fresh/full install: Install the broker package + dependencies following [https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html](https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html) (Complete sections "Installing the package" and "Defining Environmental Variables")
    - Install Beam and GCP dependencies on top of existing broker install: `pip install apache-beam[gcp]`

3. `cd` to this directory (`broker/beam`)

4. Set configs and start the job:

```bash
#-- Set configs
source beam.config
beamdir=$(pwd)
# export PYTHONPATH="${PYTHONPATH}:${beamdir}/beam_helpers"

#-- Start the ztf processing Dataflow job
cd ztf_value_added
python beam_ztf_value_added.py \
            --experiments use_runner_v2 \
            --setup_file ${setup_file_valadd} \
            --runner ${runner} \
            --region ${region} \
            --project ${PROJECTID} \
            --job_name ${dataflow_job_name_valadd} \
            --max_num_workers ${max_num_workers_valadd} \
            --staging_location ${staging_location} \
            --temp_location ${temp_location} \
            --PROJECTID ${PROJECTID} \
            --source_PS_ztf ${source_PS_ztf} \
            --sink_BQ_salt2 ${sink_BQ_salt2} \
            --sink_PS_exgalTrans ${sink_PS_exgalTrans} \
            --sink_PS_salt2 ${sink_PS_salt2} \
            --streaming \
            --update  # use only if updating a currently running job; job_name must match current job

# Start the ztf -> BQ job
cd ${beamdir} && cd ztf_bq_sink
python beam_ztf_bq_sink.py \
            --experiments use_runner_v2 \
            --setup_file ${setup_file_bqsink} \
            --runner ${runner} \
            --region ${region} \
            --project ${PROJECTID} \
            --job_name ${dataflow_job_name_bqsink} \
            --max_num_workers ${max_num_workers_bqsink} \
            --staging_location ${staging_location} \
            --temp_location ${temp_location} \
            --PROJECTID ${PROJECTID} \
            --source_PS_ztf ${source_PS_ztf} \
            --sink_BQ_originalAlert ${sink_BQ_originalAlert} \
            --streaming \
            --update  # use only if updating a currently running job
cd beamdir
```

5. View the [Dataflow job in the GCP Console](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
