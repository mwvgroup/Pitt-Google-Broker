A Reference for Common Setup Requirements
==========================================

..contents:: title
    :depth: 2

Authenticate
----------------

For API calls via python, are you need for authentication is to set two environment variables.
For API calls via the `gcloud` CLI, there is an additional authentication step.

Set environment variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

The following environment variables are used to authenticate you to make API calls to Google Cloud.

For reference, our current project IDs are:

* production project: ``ardent-cycling-243415``
* testing project: ``avid-heading-329016``

You will also need to know that path to your local authentication key file (service account credentials), which you downloaded during :ref:`broker/run-a-broker-instance/initial-setup:Setup Local Environment`.

.. code-block:: bash

   # fill a Google Cloud project ID (see above for some options)
   export GOOGLE_CLOUD_PROJECT=<project_id>
   # fill in the path to your service account key file associated with the above project
   export GOOGLE_APPLICATION_CREDENTIALS=<path/to/GCP_auth_key.json>

Authenticate to gcloud
~~~~~~~~~~~~~~~~~~~~~~~

You should only need to run this once, unless you want to switch the project or service account that gcloud is using.

.. code-block:: bash

   # make sure you set your environment variables in the previous step.
   gcloud auth activate-service-account \
       --project="${GOOGLE_CLOUD_PROJECT}" \
       --key-file="${GOOGLE_APPLICATION_CREDENTIALS}"

Install broker-utils
---------------------

Our broker-utils python library contains many functions that are helpful in working both alerts and GCP services.
It can be installed using
(you may want to activate a Conda environment before installing):

.. code-block:: bash

    pip install pgb-broker-utils
