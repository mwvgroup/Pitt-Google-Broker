Initial Setup
=============

Our broker is based in `Google Cloud
Platform <https://cloud.google.com/>`__ (GCP). To access the data, you
need a (free) GCP project of your own with a configured service account
authorizing your use of Google's API. You can then use either
command-line or Python tools to access our Pub/Sub streams, BigQuery
databases, and file in Cloud Storage.

This document contains instructions to: 1. Create a new GCP project (and
delete it when you are done). 2. Create a service account and configure
authentication on your local (or wherever) machine. 3. Enable the APIs
on your project and install the command-line and/or Python tools.

There are two methods available to accomplish the above: - `Method A:
Command line <#method-a-command-line>`__. Install the CLI and do
everything from the command line. - `Method B: GCP
Console <#method-b-gcp-console>`__. Use the web Console for the GCP
setup portion.

This process only needs to be done once per project/local machine.

Method A: Command line
----------------------

Fill in these three lines as desired for your new GCP project:

.. code:: bash

    # choose your GCP Project ID. it must be unique, so at least add a number here
    PROJECT_ID=my-pgb-project

    # choose a name for your service account
    SA_NAME=mypgb-service-account

    # choose a location for your key file
    KEY_PATH=/local/path/for/GCP_auth_key.json

Install the CLI
(`cloud.google.com/sdk <https://cloud.google.com/sdk>`__) and connect it
to your Google account (go
`here <https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp>`__
if you need to create one). The CLI includes the tools gcloud (general
purpose), bq (BigQuery), and gsutil (Cloud Storage).

.. code:: bash

    # Windows: see https://cloud.google.com/sdk/docs/downloads-interactive#windows

    # Linux and MacOS:
    curl https://sdk.cloud.google.com | bash
    # follow the directions

    # open a new terminal or restart your shell
    # exec -l $SHELL

    # connect to the Google account you want to use
    gcloud init
    gcloud auth login
    # this will open a browser and prompt you for authorization. follow the instructions

Create a new GCP project and set it as your local default.

.. code:: bash

    gcloud projects create $PROJECT_ID
    gcloud config set project $PROJECT_ID

Create an owner service account and download an authentication key file.

.. code:: bash

    gcloud iam service-accounts create $SA_NAME
    gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/owner"
    gcloud iam service-accounts keys create $KEY_PATH --iam-account=$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com

Set local environment variables that will be used by API calls.

.. code:: bash

    export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
    export GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH

Enable the desired APIs. Here are some options:

.. code:: bash

    gcloud services enable pubsub.googleapis.com
    gcloud services enable bigquery.googleapis.com
    gcloud services enable storage.googleapis.com

Install the desired Python APIs. Here are some options:

.. code:: bash

    # Option 1: install PGB's package to use our wrapper functions to make API calls
    #           this also installs all Google Cloud APIs listed in Option 2
    pip install pgb-utils

    # Option 2: install only the Google Cloud APIs that you want to use. some options:
    pip install google-cloud-pubsub
    pip install google-cloud-bigquery
    pip install google-cloud-storage

To permanently DELETE the project when you are done, use (uncomment the
line):

.. code:: bash

    # gcloud projects delete $PROJECT_ID

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

   GCP setup
**Step 2**

Follow the instructions at `Creating a service
account <https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account>`__
to create a service account and download the key file for
authentication.

Set local environment variables that will be used by API calls.

.. code:: bash

    # insert your project ID from step 1:
    PROJECT_ID=my-pgb-project
    # insert the path to the key file you downloaded
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

    # Option 1: install PGB's package to use our wrapper functions to make API calls
    #           this also installs all Google Cloud APIs listed in Option 2
    pip install pgb-utils

    # Option 2: install only the Google Cloud APIs that you want to use. some options:
    pip install google-cloud-pubsub
    pip install google-cloud-bigquery
    pip install google-cloud-storage

**To delete**

To permanently DELETE the project when you are done, go to the `Cloud
Resource
Manager <https://console.cloud.google.com/cloud-resource-manager>`__,
select your project, and click "DELETE".
