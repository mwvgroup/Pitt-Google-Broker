Initial Setup
=============

**Learning Objectives:**

- Complete the initial setup for data access

    1. Create a new GCP project.
    2. Create a service account and configure authentication on a local machine.
    3. Enable the APIs on your project and install related tools locally.

Our broker lives on `Google Cloud
Platform <https://cloud.google.com/>`__ (GCP).
To access the data you
need a free GCP project of your own, with a configured service account
giving you access to Google's APIs.
You can then connect using many different languages;
our tutorials (except this one) demonstrate Python and command-line methods.

Complete this tutorial one of two ways:

-   :ref:`method-a-command-line`. Install the CLI and do
    everything from the command line.
-   :ref:`method-b-gcp-console`. Use the web Console for the GCP setup portion.

This setup only needs to be done once per project/local machine.

.. _method-a-command-line:

Method A: Command line
----------------------

Choose some parameters that will be used to create and configure your GCP project:

.. code:: bash

    # project ID. it must be unique, so at least add a number here
    PROJECT_ID=my-pgb-project

    # service account name
    SA_NAME=my-service-account

    # local path to store your key file, ending with .json
    KEY_PATH=/local/path/for/GCP_auth_key.json

    # nothing to choose here, just set this variable
    SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"


We will use the `gcloud <https://cloud.google.com/sdk/gcloud>`__
tool to manage the project.
Using the commands below, install it and connect it to a Google or Gmail account (go
`here <https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp>`__
if you need to create one).
This installs a CLI package that also includes the
`bq <https://cloud.google.com/bigquery/docs/bq-command-line-tool>`__ and
`gsutil <https://cloud.google.com/storage/docs/gsutil>`__ tools.

.. code:: bash

    # install the CLI
    curl https://sdk.cloud.google.com | bash  # Linux and MacOS:
        # Windows: see https://cloud.google.com/sdk/docs/downloads-interactive#windows
    # follow the directions

    # open a new terminal or restart your shell
    # exec -l $SHELL

    # connect to a Google account
    gcloud init
    gcloud auth login
    # this will open a browser and prompt you for authorization. follow the instructions

Create a new GCP project and set it as your local default.

.. code:: bash

    gcloud projects create $PROJECT_ID
    gcloud config set project $PROJECT_ID

Create a service account, give it owner permissions, and download an authentication key file.

.. code:: bash

    gcloud iam service-accounts create $SA_NAME
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/owner"
    gcloud iam service-accounts keys create $KEY_PATH --iam-account=$SA_EMAIL

Set local environment variables that will be used by API calls.

.. code:: bash

    export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
    export GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH

Enable the desired APIs. Here are some options:

.. code:: bash

    gcloud services enable bigquery.googleapis.com
    gcloud services enable pubsub.googleapis.com
    gcloud services enable storage.googleapis.com

Install the desired Python APIs. Here are some options:

.. code:: bash

    # Option 1:
    pip install pgb-utils
    # most of our tutorials use this
    # it also installs everything listed below

    # Option 2: install only specific Google Cloud APIs. some options:
    pip install google-cloud-bigquery
    pip install google-cloud-pubsub
    pip install google-cloud-storage

To permanently DELETE the project when you are done, use (uncomment the
line):

.. code:: bash

    # gcloud projects delete $PROJECT_ID

.. _method-b-gcp-console:

Method B: GCP Console
---------------------

**Step 1**

Go to the `Cloud Resource
Manager <https://console.cloud.google.com/cloud-resource-manager>`__ and
login with a Google account (go
`here <https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp>`__
if you need to create one). Click "Create Project" (A). Enter a project
name and **write down the project ID (B)** for the following code. Click
"Create".

.. figure:: gcp-setup.png
   :alt: GCP setup

**Step 2**

Follow the instructions at `Creating a service
account <https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account>`__
to create a service account and download the key file for
authentication.

Set local environment variables that will be used by API calls.

.. code:: bash

    # insert your project ID from step 1:
    PROJECT_ID=my-pgb-project
    # insert the path to the key file you just downloaded
    KEY_PATH=/local/path/to/GCP_auth_key.json

    export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
    export GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH

**Step 3**

Enable the desired APIs. Go to the `API
Library <https://console.cloud.google.com/apis/library>`__, click on the
API you want, then click "Enable". Here are direct links to the most
common APIs. Note that you may need to select your project from the
dropdown at the top. -
`Pub/Sub <https://console.cloud.google.com/apis/library/pubsub.googleapis.com>`__
-
`BigQuery <https://console.cloud.google.com/apis/library/bigquery.googleapis.com>`__
- `Cloud
Storage <https://console.cloud.google.com/apis/library/storage-component.googleapis.com>`__

Install the desired Python APIs. Here are some options:

.. code:: bash

    # Option 1:
    pip install pgb-utils
    # most of our tutorials use this
    # it also installs everything listed below

    # Option 2: install only specific Google Cloud APIs. some options:
    pip install google-cloud-bigquery
    pip install google-cloud-pubsub
    pip install google-cloud-storage

**To delete**

To permanently DELETE the project when you are done, go to the `Cloud
Resource
Manager <https://console.cloud.google.com/cloud-resource-manager>`__,
select your project, and click "DELETE".
