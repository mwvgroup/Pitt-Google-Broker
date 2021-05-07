# Beam + Dataflow Data Processing Pipeline

See [`beam-dataflow-primer.md`](beam_dataflow_primer.md) for intros to Beam and Dataflow.
It is interspersed with references to components of the pipeline(s) that we deploy here.

To manually start the jobs (defined in
[`value_added/value_added.py`](value_added/value_added.py)
and [`bq_sink/bq_sink.py`](bq_sink/bq_sink.py)):

1. Clone this repo.

2. Set up your environment (a Conda env is recommended). Either:
    - Fresh/full install: Install the broker package + dependencies following [https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html](https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html) (Complete sections "Installing the package" and "Defining Environmental Variables")
    - Install Beam and GCP dependencies on top of existing broker install: `pip install apache-beam[gcp]`

3. `cd` to this directory (`broker/beam`)

4. Set configs and start the jobs:

```bash
#-- Set configs
survey=ztf  # use the same survey used in broker setup
testid=mytest  # use the same testid used in broker setup
PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
beamdir=$(pwd)

source jobs.config "$PROJECT_ID" "$testid" "$beamdir" "$survey"

#-- Start the ztf value-added processing Dataflow job
cd value_added
python3 value_added.py \
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
            --SURVEY ${survey} \
            --TESTID ${testid} \
            --source_PS_alerts ${source_PS_alerts} \
            --sink_BQ_salt2 ${sink_BQ_salt2} \
            --sink_CS_salt2 ${sink_CS_salt2} \
            --sink_PS_pure ${sink_PS_pure} \
            --sink_PS_exgalTrans ${sink_PS_exgalTrans} \
            --sink_PS_salt2 ${sink_PS_salt2} \
            --salt2_SNthresh ${salt2_SNthresh} \
            --salt2_minNdetections ${salt2_minNdetections} \
            --streaming \
            --update  # use only if updating a currently running job

# Once the job starts, use “Ctrl + C” to regain control of the terminal.

# Start the ztf -> BQ job
cd ${beamdir} && cd bq_sink
python bq_sink.py \
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
            --SURVEY ${survey} \
            --TESTID ${testid} \
            --source_PS_alerts ${source_PS_alerts} \
            --sink_BQ_alerts ${sink_BQ_alerts} \
            --sink_BQ_diasource ${sink_BQ_diasource} \
            --streaming \
            --update  # use only if updating a currently running job

# Once the job starts, use “Ctrl + C” to regain control of the terminal.
```

5. View the [Dataflow job(s) in the GCP Console](https://console.cloud.google.com/dataflow/jobs)
