# Beam + Dataflow Data Processing Pipeline

See [`beam-dataflow-primer.md`](beam-dataflow-primer.md) for intros to Beam and Dataflow.
It is interspersed with references to components of the pipeline that we deploy here.

To start the job (which is defined in [`ztf-proc.py`](ztf-proc.py)):

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
cd ztf_proc
python ztf-proc.py \
            --experiments use_runner_v2 \
            --setup_file ${setup_file_proc} \
            --runner ${runner} \
            --region ${region} \
            --project ${PROJECTID} \
            --job_name ${dataflow_job_name_proc} \
            --max_num_workers ${max_num_workers_proc} \
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
python ztf-bq-sink.py \
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
