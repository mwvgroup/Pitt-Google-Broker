Cloud Configuration
===================

Before deploying a broker instance to the cloud, you will need to create and
authenticate a new cloud project. This project, and it's unique Id, will be
used to organize the various resources used by the deployed system. For
information on creating a new GCP project, see:
[https://cloud.google.com/resource-manager/docs/creating-managing-projects](https://cloud.google.com/resource-manager/docs/creating-managing-projects).

Once your project has been created, take note of the unique project Id as it
will be required at multiple points throughout the deployment process.

Authentic CLI Tools
-------------------

You will need to authenticate the `gcloud` command line tools
so that they can access your google cloud project. This is accomplished using
the project Id noted earlier:

.. code-block:: bash

   gcloud auth login # Login to GCP
   gcloud config set project [PROJECT-ID]  # Configure the project ID
   gcloud auth configure-docker # Allow access for deploying docker images

Creating GCP Services
---------------------
