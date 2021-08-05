Initial Setup
=============

**Learning Objectives:**

Complete the initial setup required for data access:

    1. :ref:`Create a new GCP project.
       <access-data/tutorials/initial-setup:Step 1: Create a GCP project>`
    2. :ref:`Create a service account and configure authentication on a local machine.
       <access-data/tutorials/initial-setup:Step 2: Configure authentication>`
    3. :ref:`Enable the APIs on your project and install related tools locally.
       <access-data/tutorials/initial-setup:Step 3: Enable and install APIs>`

Our broker lives on `Google Cloud
Platform <https://cloud.google.com/>`__ (GCP).
To access the data you
need a free GCP project of your own, with a configured service account
authenticating your access to Google's APIs.
You can then connect using many different languages;
our tutorials (except this one) demonstrate Python and command-line methods.

This setup only needs to be done once per project/local machine.

The end of this tutorial includes instructions to
:ref:`delete the project <delete-project>`.


Step 1: Create a GCP project
------------------------------

Go to the Google `Cloud Resource
Manager <https://console.cloud.google.com/cloud-resource-manager>`__ and
login with a Google or Gmail account (go
`here <https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp>`__
if you need to create one). Click "Create Project" (A). Enter a project
name and **write down the project ID (B)**, you will need it below.
Click "Create".

.. figure:: gcp-setup.png
   :alt: GCP setup


Step 2: Configure authentication
---------------------------------

**On GCP:**

    Go to Google's "Getting started with authentication" page and complete the
    section `Creating a service
    account <https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account>`__
    where you will create a service account in your project
    and download a JSON key file for authentication.

**Locally:**

    Open a shell on your local machine and execute the following code to set
    two environment variables.
    They will be used in the background by the APIs to connect to your project
    and authenticate your calls to various services like Pub/Sub or BigQuery.

    .. code-block:: console

        $ # insert your project ID from step 1:
        $ PROJECT_ID=my-pgb-project

        $ # insert the path to the key file you just downloaded
        $ KEY_PATH=/local/path/to/GCP_auth_key.json

        $ # set the environment variables
        $ export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
        $ export GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH


Step 3: Enable and install APIs
---------------------------------

**On GCP:**

    Enable the desired APIs in your project.
    Below are direct links to the APIs needed for our tutorials.
    You only need to enable the ones you want to use
    (e.g., to complete the Pub/Sub Streams tutorial, enable the Pub/Sub API).
    Follow the link below, make sure your project is selected in the dropdown menu
    at the top of the webpage, then click "Enable".

    - `BigQuery
      <https://console.cloud.google.com/apis/library/bigquery.googleapis.com>`__
      (databases)
    - `Cloud Storage
      <https://console.cloud.google.com/apis/library/storage-component.googleapis.com>`__
      (file storage)
    - `Pub/Sub <https://console.cloud.google.com/apis/library/pubsub.googleapis.com>`__
      (message streams)

    Experienced users may wish to enable other APIs.
    This can be done from the
    `API Library <https://console.cloud.google.com/apis/library>`__:
    search for and click on the API you want, then click "Enable".

**Locally:**

    Install the desired :ref:`Python <python-installs>` and/or
    :ref:`command-line <cli-installs>` tools.
    Our tutorials demonstrate both methods;
    you can choose the one you are most comfortable with.

.. _python-installs:

Python API Installs
~~~~~~~~~~~~~~~~~~~

Recommended method:

    Install the pgb-utils package in a Python3 environment using the code below.
    This will install the Google Cloud BigQuery, Pub/Sub, and Cloud Storage APIs,
    along with our package which contains working examples of using
    the Google APIs to access data from the Pitt-Google project.
    It will also install some standard packages like Astropy and Pandas.

    Our tutorials use this package to demonstrate Python calls.

    .. code-block:: console

        $ pip install pgb-utils

Alternate method:

    Experienced users who just want to use the Google Cloud APIs directly can
    install the packages individually.
    Here are commands to install the BigQuery, Pub/Sub, and Cloud Storage APIs:

    .. code-block:: console

        $ pip install google-cloud-bigquery
        $ pip install google-cloud-pubsub
        $ pip install google-cloud-storage

    See `Python Cloud Client Libraries
    <https://cloud.google.com/python/docs/reference>`__
    for a complete list of available APIs.

.. _cli-installs:

Command-line interface install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To access data from the command line, install and configure the CLI
using the code below.
This will install three tools: gcloud, bq, and gsutil.
Their use is demonstrated in our tutorials.

.. code-block:: console

    $ # Windows:
    $ # see https://cloud.google.com/sdk/docs/downloads-interactive#windows

    $ # Linux and MacOS:
    $ curl https://sdk.cloud.google.com | bash
    $ # follow the directions

    $ # open a new terminal or restart your shell

    $ # either reactivate your Conda environment,
    $ # or reset the environment variables from step 2

    $ # connect the CLI to your Google account:
    $ gcloud init
    $ # follow the directions
    $ # note this may open a browser and ask you to complete the setup there

    $ # set your new project as the default:
    $ gcloud config set project $GOOGLE_CLOUD_PROJECT


.. _delete-project:

Cleanup: Delete a GCP project
-------------------------------

If you are done with your GCP project you can permanently delete it.

Go to the `Cloud Resource
Manager <https://console.cloud.google.com/cloud-resource-manager>`__,
select your project, and click "DELETE".
