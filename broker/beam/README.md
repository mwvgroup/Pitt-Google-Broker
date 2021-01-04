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
PROJECTID=ardent-cycling-243415
# sources and sinks
source_PS_ztf=projects/ardent-cycling-243415/topics/ztf_alert_data
sink_BQ_originalAlert=ztf_alerts.alerts
sink_BQ_salt2=ztf_alerts.salt2
sink_PS_exgalTrans=projects/${PROJECTID}/topics/ztf_exgalac_trans
sink_PS_salt2=projects/${PROJECTID}/topics/ztf_salt2
# generic job configs
region=us-central1
beam_bucket=ardent-cycling-243415_dataflow-test
staging_location=gs://${beam_bucket}/staging
temp_location=gs://${beam_bucket}/temp
runner=DataflowRunner
# python setup file
setup_file=/Users/troyraen/Documents/PGB/repo/broker/beam/setup.py

#-- Start the ztf processing Dataflow job
dataflow_job_name=production-ztf-ps-exgal-salt2
max_num_workers=10

python ztf-proc.py \
            --experiments use_runner_v2 \
            --setup_file ${setup_file} \
            --runner ${runner} \
            --region ${region} \
            --project ${PROJECTID} \
            --job_name ${dataflow_job_name} \
            --max_num_workers ${max_num_workers} \
            --staging_location ${staging_location} \
            --temp_location ${temp_location} \
            --PROJECTID ${PROJECTID} \
            --source_PS_ztf ${source_PS_ztf} \
            --sink_BQ_salt2 ${sink_BQ_salt2} \
            --sink_PS_exgalTrans ${sink_PS_exgalTrans} \
            --sink_PS_salt2 ${sink_PS_salt2} \
            --streaming \
            --update  # use only if updating a currently running job; job_name must match current job

# ztf -> BQ job
dataflow_job_name=production-ztf-ps-bq
max_num_workers=20

python ztf-bq-sink.py \
            --experiments use_runner_v2 \
            --setup_file ${setup_file} \
            --runner ${runner} \
            --region ${region} \
            --project ${PROJECTID} \
            --job_name ${dataflow_job_name} \
            --max_num_workers ${max_num_workers} \
            --staging_location ${staging_location} \
            --temp_location ${temp_location} \
            --PROJECTID ${PROJECTID} \
            --source_PS_ztf ${source_PS_ztf} \
            --sink_BQ_originalAlert ${sink_BQ_originalAlert} \
            --streaming \
            --update  # use only if updating a currently running job
```

5. View the [Dataflow job in the GCP Console](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
