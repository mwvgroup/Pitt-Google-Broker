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

To install the ``broker`` package, download the package source code from
`GitHub`_ and run the included ``setup.py`` file:

.. code-block:: bash

    git clone https://github.com/mwvgroup/Pitt-Google-Broker
    cd Pitt-Google-Broker
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
defined in the working environment. If either variable is not found, a warning
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



.. _GitHub: https://github.com/mwvgroup/Pitt-Google-Broker
.. _Create a project: https://cloud.google.com/resource-manager/docs/creating-managing-projects
.. _Authenticate: https://cloud.google.com/docs/authentication/getting-started
.. _here: https://cloud.google.com/resource-manager/docs/creating-managing-projects
.. _Google Cloud Platform: https://cloud.google.com
.. _conda documentation: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html
