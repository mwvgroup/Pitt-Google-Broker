Cloud Configuration
===================

Before deploying a broker instance to the cloud, you will need to create and
authenticate a new cloud project. This project, and it's unique Id, will be
used to organize the various resources used by the deployed system. For
information on creating a new GCP project, see:
`https://cloud.google.com/resource-manager/docs/creating-managing-projects <https://cloud.google.com/resource-manager/docs/creating-managing-projects>`.

Once your project has been created, take note of the unique project Id as it
will be required at multiple points throughout the deployment process.

Authenticate CLI Tools
-------------------

You will need to authenticate the `gcloud` command line tools
so that they can access your google cloud project. This is accomplished using
the project Id noted earlier:

.. code-block:: bash

   gcloud auth login # Login to GCP
   gcloud config set project [PROJECT-ID]  # Configure the project ID
   gcloud auth configure-docker # Allow access for deploying docker images

Setting up GCP
--------------

You will need to set up a handful of tools in GCP. The broker package provides
an automated setup tool that automates these tasks for convenience.

.. code-block:: python
   :linenos:

    from broker.gcp_setup import auto_setup

    # See a list of changes that will be made to your GCP project
    help(auto_setup)

    # Setup your GCP project
    auto_setup()

Deploying the ``stream_GCS_to_BQ`` Cloud Function
-------------------------------------------------

The ``stream_GCS_to_BQ`` function must be deployed from the command line as a
Google Cloud Function so that it listens to the appropriate bucket(s) for new
alert Avro files and appends the data to a BigQuery table. The Google Cloud SDK
must be installed first (see :doc:`dependencies.rst`). The following script automates the
deployment. Note that it may take a couple of minutes to complete.

.. code-block::bash
    :linenos:

    ./broker/cloud_functions/GCS_to_BQ.sh
