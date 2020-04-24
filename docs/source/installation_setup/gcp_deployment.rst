Deploying a Broker Instance
===========================

This document outlines how to deploy a version of the Pitt-Google Broker (PGB)
to the Google Cloud Platform (GCP). It is intended as a reference for
developers interested in deploying their own dedicated or down-stream broker
system on GCP, or for those who would simply like to better understand the PGB
pipeline.

Before proceeding with installation, you will need to create and
authenticate a new GCP project. This project, and it's unique Id, will be
used to organize the various resources used by the deployed broker. For
information on creating a new GCP project, see:
[https://cloud.google.com/resource-manager/docs/creating-managing-projects](https://cloud.google.com/resource-manager/docs/creating-managing-projects).
