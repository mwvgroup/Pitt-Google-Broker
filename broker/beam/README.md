# PGB Alert Broker Beam Pipeline

To start the job:

1. Install Apache Beam with GCP tools: `pip install apache-beam[gcp]`

2. Clone this repo

3. `cd` to this directory (`broker/beam`)

4. Run the following:

```bash
region='us-central1'
python -m ztf-beam \
            --region ${region} \
            --experiments use_runner_v2 \
            --setup_file /home/troy_raen_pitt/PGB_testing/deploy2cloud_Aug2020/beam-workflow/setup.py \
            --streaming \
            # --update  # use this to update a currently running job
```

5. View the [Dataflow job in the GCP Console](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
