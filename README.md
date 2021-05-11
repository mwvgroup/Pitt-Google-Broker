# Pitt-Google Alert Broker

The Pitt-Google broker is an astronomical alert broker that is being developed for large scale surveys of the night sky, particularly the upcoming [Vera Rubin Observatory's Legacy Survey of Space and Time](https://www.lsst.org/) (LSST).
We currently process and serve the [Zwicky Transient Facility](https://www.ztf.caltech.edu/)'s (ZTF) nightly alert stream.
The broker runs on the Google Cloud Platform ([GCP](https://cloud.google.com)).

---

## Access the Data

See [Pitt-Google-Tutorial-Code-Samples.ipynb](https://github.com/mwvgroup/Pitt-Google-Broker/blob/master/pgb_utils/tutorials/Pitt-Google-Tutorial-Code-Samples.ipynb) for a tutorial.
Data can be accessed using Google's [Cloud SDK](https://cloud.google.com/sdk) (Python, command-line, etc.).
In addition, we offer the Python package `pgb_utils` which contains wrappers of Cloud SDK methods and other helper functions to facilitate common use cases.
See the tutorials for details.

If you run into issues or need assistance, please open an Issue on GitHub or contact troy.raen@pitt.edu.

---

## Run the Alert Broker

See [broker/README.md](broker/README.md) for information about the alert broker software and instructions on running it. The broker will connect to a survey alert stream (e.g., ZTF) and process \& redistribute the data. Those looking to __access__ the data do not need to run the broker; instead see [Access the Data](#access-the-data)

<!-- Full online documentation is available online via [Read the Docs](https://pitt-broker.readthedocs.io/en/latest/index.html). -->

---

[![python](https://img.shields.io/badge/python-3.7-g.svg)]()
[![Build Status](https://travis-ci.com/mwvgroup/Pitt-Google-Broker.svg?branch=master)](https://travis-ci.com/mwvgroup/Pitt-Google-Broker)
[![Documentation Status](https://readthedocs.org/projects/pitt-broker/badge/?version=latest)](https://pitt-broker.readthedocs.io/en/latest/?badge=latest)
