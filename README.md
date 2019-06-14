# Pitt LSST Broker

[![python](https://img.shields.io/badge/python-3.7-g.svg)]()
[![Build Status](https://travis-ci.com/mwvgroup/Pitt-Broker.svg?branch=master)](https://travis-ci.com/mwvgroup/Pitt-Broker)
[![Documentation Status](https://readthedocs.org/projects/pitt-broker/badge/?version=latest)](https://pitt-broker.readthedocs.io/en/latest/?badge=latest)

Data from the Large Synoptic Survey Telescope ([LSST](https://www.lsst.org)) will be distributed through three distinct avenues. The first is a real-time stream of alerts that provides information on transient targets within 60 seconds of observation. The second is a daily data release, which contains the same information as the 60-second alerts plus some additional information. The last data product will be a yearly data release.

The 60-second alert stream will not be made available to the public (at least not in its entirety). Instead, LSST will rely on a small number of (~7) community developed *broker* systems to publically relay the information. This repo represents the construction of an LSST broker designed to run on the Google Cloud Platform ([GCP](https://cloud.google.com)) using alerts from the Zwicky Transient Facility ([ZTF](https://www.ztf.caltech.edu)) as a testing ground.

Full online documentation is available online via [Read the Docs](https://pitt-broker.readthedocs.io/en/latest/index.html).
