# Pitt-Google Alert Broker

The Pitt-Google broker is an astronomical alert broker that is being developed for large scale surveys of the night sky, particularly the upcoming [Vera Rubin Observatory's Legacy Survey of Space and Time](https://www.lsst.org/) (LSST).
We currently process and serve the [Zwicky Transient Facility](https://www.ztf.caltech.edu/)'s (ZTF) nightly alert stream.

## Access the Data

See [Pitt-Google-Tutorial-Code-Samples.ipynb](https://github.com/mwvgroup/Pitt-Google-Broker/blob/master/pgb_utils/tutorials/Pitt-Google-Tutorial-Code-Samples.ipynb) for a tutorial.
Data can be accessed using Google's [Cloud SDK](https://cloud.google.com/sdk) (Python, command-line, etc.).
In addition, we offer the Python package `pgb_utils` which contains wrappers of Cloud SDK methods and other helper functions to facilitate common use cases.
See the tutorials for details.

If you run into issues or need assistance, please open an Issue on GitHub or contact troy.raen@pitt.edu.

---
## Run the Alert Broker

See [broker/README.md](broker/README.md) for information about the alert broker software and instructions on running it. The broker will connect to a survey alert stream (e.g., ZTF) and process \& redistribute the data. Those looking to __access__ the data do NOT need to run the broker; instead see [Access the Data](#access-the-data)

- [Broker Architecture](#broker-architecture)
- [Setup the Broker for the First Time](#setup-the-broker-for-the-first-time)
- [Run Nightly Broker](#run-nightly-broker)
- [Note on Resources for Test Runs](#note-on-resources-for-test-runs)
- [original README](#ogread)

__Useful tutorial/reference docs__
- [__broker/README__.md](broker/README.md)
- [broker/consumer/__kafka_console_connect__.md](broker/consumer/kafka_console_connect.md)
- [broker/beam/__beam_dataflow_primer__.md](broker/beam/beam_dataflow_primer.md)


---

# Setup the Broker for the First Time
<!-- fs -->
1. Setup and configure a new Google Cloud Platform (GCP) project.
    - [Instructions in our current docs](https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html). We would need to follow pieces of the "Installation" and "Defining Environmental Variables" sections. Our project is already setup, so leaving out most of the details for now.

2. Install GCP tools on your machine:
    - [Google Cloud SDK](https://cloud.google.com/sdk/docs/install): Follow the instructions at the link. (This installs `gcloud`, `gsutil` and `bq` command line tools). I use a minimum version of Google Cloud SDK 323.0.0.
    - [Cloud Client Libraries for Python](https://cloud.google.com/python/docs/reference): Each service requires a different library; the ones we need are (I hope) all listed in the `requirements.txt` in this directory. Install them with (e.g., ) `pip install -r requirements.txt`.

3. Follow instructions in [broker/README.md](broker/README.md) to complete the setup.
<!-- fe Setup the Broker -->

---
<a name="ogread"></a>
The following is the original README:
<!-- fs -->

[![python](https://img.shields.io/badge/python-3.7-g.svg)]()
[![Build Status](https://travis-ci.com/mwvgroup/Pitt-Google-Broker.svg?branch=master)](https://travis-ci.com/mwvgroup/Pitt-Google-Broker)
[![Documentation Status](https://readthedocs.org/projects/pitt-broker/badge/?version=latest)](https://pitt-broker.readthedocs.io/en/latest/?badge=latest)

Data from the Large Synoptic Survey Telescope ([LSST](https://www.lsst.org)) will be distributed through three distinct avenues. The first is a real-time stream of alerts that provides information on transient targets within 60 seconds of observation. The second is a daily data release, which contains the same information as the 60-second alerts plus some additional information. The last data product will be a yearly data release.

The 60-second alert stream will not be made available to the public (at least not in its entirety). Instead, LSST will rely on a small number of (~7) community developed *broker* systems to publically relay the information. This repo represents the construction of an LSST broker designed to run on the Google Cloud Platform ([GCP](https://cloud.google.com)) using alerts from the Zwicky Transient Facility ([ZTF](https://www.ztf.caltech.edu)) as a testing ground.

Full online documentation is available online via [Read the Docs](https://pitt-broker.readthedocs.io/en/latest/index.html).

<!-- fe OG readme -->
