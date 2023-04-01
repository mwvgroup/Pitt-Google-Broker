Initial Setup
==============

Setup a Google Cloud Platform project and your local environment.

Method A:

-  `Create a GCP Project`_
-  `Setup Local Environment`_

Method B: Alternately, you can skip down to to the `Command line`_ section and try
completing the full process from the command line.

Note that neither method has been fully tested, end-to-end, on a new GCP account and
project.

Create a GCP Project
--------------------

1. Create a new Google Cloud Platform (GCP) project.

-  A. Go to the `Cloud Resource
   Manager <https://console.cloud.google.com/cloud-resource-manager>`__
   and click "Create Project".
-  B. Write down your Project ID for the following code.
-  C. Click "Create".

See `Creating and managing
projects <https://cloud.google.com/resource-manager/docs/creating-managing-projects>`__
for more information, including instructions for creating a project
programatically.

2. Enable billing and APIs for required services.

.. code:: bash

    # enable APIs
    gcloud services list --available  # check what's available
    gcloud services enable pubsub.googleapis.com  # enable pubsub
    # will need others like bigquery and storage

Setup Local Environment
-----------------------

Broker instances *run* 100% in the Google Cloud, as determined by the
code in the ``broker`` package. You can *develop* the code and/or
*deploy* an instance to the Cloud from your local machine. Setup your
environment as follows:

1. **Install Google Cloud SDK command-line tools** using one of the
   following options. Included tools: gcloud, gsutil, and
   bq. Version 323.0.0 or above is recommended.

   -  `install from the command
      line <https://cloud.google.com/sdk/docs/downloads-interactive>`__
   -  `download the
      package <https://cloud.google.com/sdk/docs/install>`__

1b. You may need to authenticate gcloud using the code below. You
may be asked to re-authenticate occasionally in the future.

.. code:: bash

    PROJECT_ID=my-pgb-project  # replace with your GCP Project ID

    gcloud auth login  # follow the instructions to login to GCP
    gcloud config set project $PROJECT_ID  # set your project ID

2. **Install Python libraries** for `GCP
   services <https://cloud.google.com/python/docs/reference>`__ and
   other tools such as Pandas, Astropy, etc. as needed. You can install
   packages individually, or use the requirements.txt file at the top
   level of the repo. The following code creates a new
   `Conda <https://www.anaconda.com/>`__ environment and installs the
   requirements.

.. code:: bash

    # create a Conda environment (optional)
    conda create -n pgb python=3.7
    conda activate pgb

    # install the requirements. assumes txt file is in current directory
    pip3 install -r requirements.txt

**Note**: On an M1 Mac, first use Conda to install Astropy
(``conda install astropy=3.2.1``), then comment the related line out of
the requirements file before doing ``pip install``.

3. **Create a GCP service account and download a key file** for
   authentication using the following code. See `Getting started with
   authentication <https://cloud.google.com/docs/authentication/getting-started>`__
   for more information.

.. code:: bash

    PROJECT_ID=my-pgb-project  # replace with your GCP Project ID
    NAME=my-service-account  # replace with desired account name
    KEY_PATH=local/path/GCP_auth_key.json  # replace with desired path (ending in .json)

    gcloud iam service-accounts create $NAME
    gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$NAME@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/owner"
    gcloud iam service-accounts keys create $KEY_PATH --iam-account=$NAME@$PROJECT_ID.iam.gserviceaccount.com

4. **Set environment variables**

.. code:: bash

    PROJECT_ID=my-pgb-project  # replace with your GCP Project ID
    KEY_PATH=local/path/GCP_auth_key.json  # same path as in step 3
    REGION="us-central1"  # replace with the region of your choice
    ZONE="${REGION}-a"  # replace with the zone of your choice

    export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
    export GOOGLE_APPLICATION_CREDENTIALS="$KEY_PATH"
    export CLOUDSDK_COMPUTE_REGION="${REGION}"
    export CLOUDSDK_COMPUTE_ZONE="${ZONE}"

If you are using a Conda environment, you can configure the environment
variables as follows:

.. code:: bash

    PROJECT_ID=my-pgb-project  # replace with your GCP Project ID
    KEY_PATH=local/path/for/key/file.json  # same path as in step 3
    REGION="us-central1"  # replace with the region of your choice

    # log into the environment and create de/activate files
    conda activate pgb
    cd $CONDA_PREFIX
    mkdir -p ./etc/conda/activate.d
    mkdir -p ./etc/conda/deactivate.d
    touch ./etc/conda/activate.d/env_vars.sh
    touch ./etc/conda/deactivate.d/env_vars.sh

    # add environment variables
    echo "export GOOGLE_CLOUD_PROJECT='$PROJECT_ID'" >> ./etc/conda/activate.d/env_vars.sh
    echo "export GOOGLE_APPLICATION_CREDENTIALS='$KEY_PATH'" >> ./etc/conda/activate.d/env_vars.sh
    echo "export CLOUDSDK_COMPUTE_REGION='${REGION}'" >> ./etc/conda/activate.d/env_vars.sh
    echo "export CLOUDSDK_COMPUTE_ZONE='${ZONE}'" >> ./etc/conda/activate.d/env_vars.sh
    echo 'unset GOOGLE_CLOUD_PROJECT' >> ./etc/conda/deactivate.d/env_vars.sh
    echo 'unset GOOGLE_APPLICATION_CREDENTIALS' >> ./etc/conda/deactivate.d/env_vars.sh
    echo 'unset CLOUDSDK_COMPUTE_REGION' >> ./etc/conda/deactivate.d/env_vars.sh
    echo 'unset CLOUDSDK_COMPUTE_ZONE' >> ./etc/conda/deactivate.d/env_vars.sh

5. **Check that your authentication works** by making an API request.
   Here we request a list of Cloud Storage buckets (in Python):

.. code:: python

    from google.cloud import storage

    storage_client = storage.Client()
    # Make an authenticated API request
    buckets = list(storage_client.list_buckets())
    # If the request succeeded, your authentication works
    print(buckets)  # this list will be empty if you haven't created any buckets yet

Command line
------------

.. code:: bash

    # choose your GCP Project ID (it must be unique, so at least add a number here)
    PROJECT_ID=my-pgb-project
    # choose a name for your service account
    NAME=mypgb-service-account
    # choose a location for your key file
    KEY_PATH=/local/path/for/GCP_auth_key.json

    # install the SDK for the command line
        # Linux and MacOS:
    curl https://sdk.cloud.google.com | bash
        # Windows:
        # see https://cloud.google.com/sdk/docs/downloads-interactive#windows
    # follow the directions

    # open a new terminal or restart your shell
    # exec -l $SHELL

    # connect gcloud to the Google account you want to use (assumes you have one already)
    gcloud init
    gcloud auth login
    # this will open a browser and prompt you for authorization. follow the instructions

    # create the project, set it as the gcloud default, and enable the Pub/Sub API
    gcloud projects create $PROJECT_ID
    gcloud config set project $PROJECT_ID
    gcloud services enable pubsub.googleapis.com

    # create an owner service account and download a key file
    gcloud iam service-accounts create $NAME
    gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$NAME@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/owner"
    gcloud iam service-accounts keys create $KEY_PATH --iam-account=$NAME@$PROJECT_ID.iam.gserviceaccount.com

    # set environment variables
    export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
    export GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH

    # install Pub/Sub Python API
    pip install google-cloud-bigquery
    pip install google-cloud-pubsub
    pip install google-cloud-storage

    # if you would like to delete the project with you are done, use:
    # gcloud projects delete $PROJECT_ID
