Installation
============

The ``broker`` package is responsible for handling the ingestion, processing,
and distribution of alert data. Although it is capable of running locally, the
package is designed to leverage resources from the `Google Cloud Platform`_
(GCP). Before proceeding with installation, you will need to create and
authenticate a new GCP project as outlined in the following links:

- `Create a project`_: Be sure to take note of the project ID as you will
  need it later on.

- `Authenticate`_: Also take note of the path to the downloaded JSON
  credentials (file associated with the service account key).

Installing the package
----------------------

The ``broker`` package can be installed by running the ``setup.py`` file:

.. code-block:: bash

    python setup.py install --user

Any missing dependencies should automatically be installed in your Python
environment. However, if you have any issues installing the package you may
need to install the dependencies manually and then try again. Dependencies can
be installed using the ``pip`` package manager and the `requirements.txt` file:

.. code-block:: bash

    pip install -r requirements.txt

Defining Environmental Variables
--------------------------------

In order for the package to connect with GCP, you will need to specify your
GCP project ID and credentials path as environmental variables. In your
`.bash_profile` or `.bashrc` file add

.. code-block:: bash

    export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
    export GOOGLE_APPLICATION_CREDENTIALS="PATH_TO_JSON_CREDENTIALS"

The ``broker`` package will automatically check whether these variables are
defined in its working environment. If either variable is not found, a warning
will be raised on import.

Various features of the ``broker`` package support downloading astronomical
data on to your local machine. You will also need to specify this directory in
you `.bash_profile` or `.bashrc` file:

.. code-block:: bash

    export PGB_DATA_DIR="~/some/directory/name/"

The ``broker`` package can be instructed to ignore certain tests and imports
that involve connecting to GCP by defining the ``GPB_OFFLINE``
variable in your environment. The value of this variable is not important,
only whether the variable is defined. This feature is primarily used for
building docs and running tests. The behavior of the ``broker`` package
when using  ``GPB_OFFLINE`` should not be relied on in a production environment.

Installing the Google Cloud SDK
-------------------------------

The ``gcloud`` command line tool is needed to deploy a Google Cloud Function to
listen to a file storage bucket and upload new files to a BigQuery database
(see Setting up GCP below). This tool is part of the
`Google Cloud SDK https://cloud.google.com/sdk/docs`_. There are several
installation options `detailed here https://cloud.google.com/sdk/install`_.
Once the SDK is installed, initialize ``gcloud`` by following the
`instructions here https://cloud.google.com/sdk/docs/initializing`_.

Setting up GCP
--------------

You will need to set up a handful of tools in GCP. The broker package provides
two setup tools that automate these tasks for convenience.

The following Python function sets up the GCP buckets, datasets, and logging
sinks.

.. code-block:: python
   :linenos:

    from broker.gcp_setup import auto_setup

    # See a list of changes that will be made to your GCP project
    help(auto_setup)

    # Setup your GCP project
    auto_setup()

The ``stream_GCS_to_BQ`` function must be deployed from the command line as a
Google Cloud Function so that it listens to the appropriate bucket(s) for new
alert Avro files and appends the data to a BigQuery table. The Google Cloud SDK
must be installed first (see above). The following script  automates the
deployment.

.. code-block::bash
    :linenos:

    ./broker/deploy_cloudfnc.sh


.. _Create a project: https://cloud.google.com/resource-manager/docs/creating-managing-projects
.. _Authenticate: https://cloud.google.com/docs/authentication/getting-started
.. _here: https://cloud.google.com/resource-manager/docs/creating-managing-projects
.. _Google Cloud Platform: https://cloud.google.com
.. _conda documentation: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html
