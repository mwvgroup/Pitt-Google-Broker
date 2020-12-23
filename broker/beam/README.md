# PGB Alert Broker Beam Pipeline

To start the job:

1. Install Apache Beam with GCP tools: `pip install apache-beam[gcp]`

2. Clone this repo

3. `cd` to this directory (`broker/beam`)

4. Set configs and start the job:

```bash
#-- python setup
setup_file=/Users/troyraen/Documents/PGB/repo/broker/beam/setup.py
#-- pipeline options
dataflow_job_name=test-argparse
# dataflow_job_name=ztf-alert-data-ps-vizier
PROJECTID=ardent-cycling-243415
region=us-central1
max_num_workers=5
beam_bucket=ardent-cycling-243415_dataflow-test
staging_location=gs://${beam_bucket}/staging
temp_location=gs://${beam_bucket}/temp
runner=DataflowRunner
#-- sources and sinks
source_PS_ztf=projects/ardent-cycling-243415/topics/ztf_alert_data
# sink_BQ_originalAlert=ztf_alerts.alerts
sink_BQ_originalAlert=dataflow_test.ztf_alerts
# sink_BQ_salt2=ztf_alerts.salt2
sink_BQ_salt2=dataflow_test.salt2
sink_PS_exgalTrans=projects/${PROJECTID}/topics/ztf_exgalac_trans
sink_PS_salt2=projects/${PROJECTID}/topics/ztf_salt2

python ztf-beam.py \
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
            --sink_BQ_salt2 ${sink_BQ_salt2} \
            --sink_PS_exgalTrans ${sink_PS_exgalTrans} \
            --sink_PS_salt2 ${sink_PS_salt2} \
            --streaming \
            # --update  # use this to update a currently running job
```

5. View the [Dataflow job in the GCP Console](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
