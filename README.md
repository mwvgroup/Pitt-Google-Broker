# Pitt LSST Broker

[![python](https://img.shields.io/badge/python-3.7-g.svg)]()

Data from the Large Synoptic Survey Telescope ([LSST](https://www.lsst.org)) will be distributed through three distinct avenues. The first is a real-time stream of alerts that provides information on transient targets within 60 seconds of observation. The second is a daily data release, which contains the same information as the 60-second alerts plus some additional information. The last data product will be a yearly data release.

The 60-second alert stream will not be made available to the public (at least not in its entirety). Instead, LSST will rely on a small number of (~7) community developed *broker* systems to publically relay the information. This repo represents the construction of an LSST broker designed to run on the Google Cloud Platform ([GCP](https://cloud.google.com)) using alerts from the Zwicky Transient Factory ([ZTF](https://www.ztf.caltech.edu)) as a testing ground.



- [Installation Instructions](#installation-instructions)
  - [GCP Environment](#gcp-environment)
  - [Local Environment](#local-environment)
- [Downloading ZTF Data](#downloading-ztf-data)
- [Ingesting Data to GCP](#ingesting-data-to-gcp)
- [Cross Matching Targets](#cross-matching-targets)



## Installation Instructions

#### 1. GCP Environment

Before establishing the backend in GCP, you will need to create and authenticate a new project as outlined in the following links:
- [Create a project](https://cloud.google.com/resource-manager/docs/creating-managing-projects).
    - Be sure to take note of the project ID, as you will need it later on.
- [Authenticate](https://cloud.google.com/docs/authentication/getting-started)
    - Be sure to take note of the path to your downloaded JSON credentials (file associated with the service account key).

#### 2. Local Environment

To create a new conda environment, run:

```bash
conda create -n pitt_broker python=3.7
conda activate pitt_broker  # Activate the new environment
```

Note that for older versions of `conda` you may have to use the deprecated command `source activate` to activate the environment. While still in the new environment, the next step is to set the GCP project ID and credential path as environmental variables. This can be achieved by running the following after replacing `YOUR_PROJECT_ID` and `PATH_TO_CREDENTIALS` with the appropriate value:

```bash
# Go to the environment's home directory
cd $CONDA_PREFIX

# Create files to run on startup and exit
mkdir -p ./etc/conda/activate.d
mkdir -p ./etc/conda/deactivate.d
touch ./etc/conda/activate.d/env_vars.sh
touch ./etc/conda/deactivate.d/env_vars.sh

# Add environmental variables
echo 'export BROKER_PROJ_ID="YOUR_PROJECT_ID"' >> ./etc/conda/activate.d/env_vars.sh
echo 'unset BROKER_PROJ_ID' >> ./etc/conda/deactivate.d/env_vars.sh
echo 'export GOOGLE_APPLICATION_CREDENTIALS="PATH_TO_CREDENTIALS"' >> ./etc/conda/activate.d/env_vars.sh
echo 'unset GOOGLE_APPLICATION_CREDENTIALS' >> ./etc/conda/deactivate.d/env_vars.sh
```

Finally, you can install the package and exit the environment by navigating to your Pitt-Broker directory and running:

```bash
python setup.py install --user  # Install the package
conda deactivate  # Use `source deactivate` for older clients
```

If you don't need the full package installed and only need the dependancies (ie. for development purposes) these can be installed using pip.

```bash
conda activate pitt_broker
pip install -r requirements.txt
conda deactivate
```



#### 3. Sinks and Datasets

You will need to set up a handful of tools in GCP. Instead of doing this manually, the `broker` package provides a setup function in Python for convenience. (Note that the conda pitt_broker environment must be active.)

```python
from broker.gcp_setup import setup_gcp

# See a list of changes that will be made to your project
help(setup_gcp)

# Setup your GCP project
setup_gcp()
```



## Downloading ZTF Data

This project will use ZTF data for testing and development. Although the live ZTF alert stream is still in beta and isn't publically available, all alerts are submitted at the end of the day to the [ZTF public alerts archive](https://ztf.uw.edu/alerts/public/). The `broker` package provides the `ztf_archive` module which is capable of automatically downloading, parsing, and plotting results from the public archive. The following example demonstrates each of these capabilities:

```python
from broker import ztf_archive as ztfa
from matplotlib import pyplot as plt

# Download recent data from the ZTF archive.
# Note: Daily releases can be as large as several Gb
download_data()

# Retrieve the number of daily releases that have been downloaded
print(ztfa.get_number_local_releases())

# Retrieve the number of alerts that have been downloaded
# from all combined daily releases.
print(ztfa.get_number_local_alerts())

# Iterate through local alert data
for alert in ztfa.iter_alerts():
    alert_id = alert['candid']
    print(alert_id)
    break

# Get data for a specific alert id
alert_data = ztfa.get_alert_data(alert_id)
print(alert_data)

# Plot stamp images for alert data
from matplotlib import pyplot as plt

fig = plot_stamps(alert_data)
plt.show()
```



## Ingesting Data to GCP

The `alert_ingestion` module handles the insertion of ZTF alert data into BigQuery. Eventually this module will ingest data directly from the live ZTF stream, but for now, it relies on the ZTF Alert Archive described in the previous section. Data can be ingested into BigQuery through multiple avenues (see [here](https://cloud.google.com/bigquery/docs/loading-data) for an overview of options and pricing models), but the `alert_ingestion` module only provides options to *stream* or *bulk insert* methods.

```python
from broker import alert_ingestion

# To ingest alerts via the BigQuery streaming interface
alert_ingestion.stream_ingest_alerts()

# To ingest 15 alerts at a time through the streaming interface
# (The default number of alerts is 10)
alert_ingestion.stream_ingest_alerts(15)

# The same principles apply for the batch upload interface
alert_ingestion.batch_ingest_alerts(15)
```



## Cross Matching Targets

The `xmatch` module provides target crossmatching of observed targets against the Vizier catalog service.

```python
from broker import xmatch as xm

# Write a CSV file with RA, DEC:
ra_dec_path = 'mock_stream/data/alerts_radec.csv'
xm.get_alerts_ra_dec(fout=ra_dec_path)

# Query VizieR for cross matches:
xm_table = xm.get_xmatches(fcat1=ra_dec_path, cat2='vizier:II/246/out')
print(xm_table)
```
