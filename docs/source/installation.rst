Installation
============

The ``broker`` package is responsible for handling the ingestion, processing,
and distribution of alert data. Although it is capable of running locally, the
package is designed to leverage resources from the `Google Cloud Platform`_
(GCP). Before proceeding with installation, you will need to create and
authenticate a new project as outlined in the following links:

- `Create a project`_: Be sure to take note of the project ID as you will
  need it later on.

- `Authenticate`_: Also take note of the path to the downloaded JSON
  credentials (file associated with the service account key).

The following instructions also assume you already have the pip
package manager installed in your Python environment. Installation
instructions and documentation for pip is available at
`https://pip.pypa.io/en/stable/ <https://pip.pypa.io/en/stable/>`_.

Installation Without Conda
--------------------------

The `broker` package can be installed by running the `setup.py` file:

.. code:: bash

    python setup.py install --user

The pip package manager will automatically install any missing dependencies in
your Python environment. If you have any issues installing the package, you may
need to install the dependencies manually and then try again. Dependencies can
be installed with ``pip`` by running:

.. code:: bash

    pip install -r requirements.txt

In order for the package to connect with GCP, you will need to specify your
GCP project ID and credentials path as environmental variables. In your
`.bash_profile` or `.bashrc` file add

.. code:: bash

    export BROKER_PROJ_ID="YOUR_PROJECT_ID"
    export GOOGLE_APPLICATION_CREDENTIALS="PATH_TO_JSON_CREDENTIALS"

The ``broker`` package will automatically check whether these variables are
defined in its working environment. If either variable is not found, a warning
will be raised on import.

Various features of the ``broker`` package support downloading astronomical
data on to your local machine. You will also need to specify this directory in
you `.bash_profile` or `.bashrc` file:

.. code:: bash

    export PGB_DATA_DIR="~/some/directory/name/"


Installation With Conda
-----------------------

If you would like to work in a dedicated conda environment, the steps are very
similar:

.. code:: bash

   conda create -n pitt_broker python=3.7
   conda activate pitt_broker  # Activate the new environment
   python setup.py install --user  # Install the package

Note that for older versions of ``conda`` you may have to use the
deprecated command ``source activate`` to activate the environment.
More information can be found in the `conda documentation`_.

While still in your conda environment, the next step is to set the GCP
project ID and credentials path as environmental variables. This can be
achieved by running the following after replacing ``YOUR_PROJECT_ID`` and
``PATH_TO_JSON_CREDENTIALS`` with the appropriate value:

.. code:: bash

   # Go to the environment's home directory
   cd $CONDA_PREFIX

   # Create files to run on startup and exit
   mkdir -p ./etc/conda/activate.d
   mkdir -p ./etc/conda/deactivate.d
   touch ./etc/conda/activate.d/env_vars.sh
   touch ./etc/conda/deactivate.d/env_vars.sh

   # Add environmental variables
   echo 'export BROKER_PROJ_ID="YOUR_PROJECT_ID"' >> ./etc/conda/activate.d/env_vars.sh
   echo 'export GOOGLE_APPLICATION_CREDENTIALS="PATH_TO_JSON_CREDENTIALS"' >> ./etc/conda/activate.d/env_vars.sh
   echo 'export PGB_DATA_DIR="~/some/directory/name/"' >> ./etc/conda/activate.d/env_vars.sh

   echo 'unset BROKER_PROJ_ID' >> ./etc/conda/deactivate.d/env_vars.sh
   echo 'unset GOOGLE_APPLICATION_CREDENTIALS' >> ./etc/conda/deactivate.d/env_vars.sh
   echo 'unset PGB_DATA_DIR' >> ./etc/conda/deactivate.d/env_vars.sh

Finally, don't forget to exit your environment:

.. code:: bash

   conda deactivate

Setting up GCP
--------------

You will need to set up a handful of tools in GCP. Instead of doing this
manually, the broker package provides a setup function for convenience.

.. code:: python

    from broker import setup_gcp

    # See a list of changes that will be made to your GCP project
    help(setup_gcp)

    # Setup your GCP project
    setup_gcp()


Running Offline
---------------

The ``broker`` package can be instructed to ignore certain tests and imports
that involve connecting to Google Cloud by defining the ``GPB_OFFLINE``
variable in your environment. The value of this variable is not considered,
only whether the variable is defined.

.. _Create a project: https://cloud.google.com/resource-manager/docs/creating-managing-projects
.. _Authenticate: https://cloud.google.com/docs/authentication/getting-started
.. _here: https://cloud.google.com/resource-manager/docs/creating-managing-projects
.. _Google Cloud Platform: https://cloud.google.com
.. _conda documentation: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html