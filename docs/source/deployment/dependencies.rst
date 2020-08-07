Local Dependencies
==================

In order to deploy a broker instance to the cloud, you will need to have a set of
command line tools available on your local machine. Although these dependencies
are **not** required by the deployed broker to run, they are require
to deploy and manage the broker instance.

.. important::

.. _gcloud:

Google Cloud SDK
----------------

The ``gcloud`` command line API is used to handle administrative tasks
within the Google Cloud Platform. Up to date installation instructions are available at
`https://cloud.google.com/sdk/install <https://cloud.google.com/sdk/install>`_.

After installation is finished, please ensure that ``gcloud`` is available in the
system ``PATH``. If you already have ``gcloud`` installed, please ensure that is
up to date:

.. code-block:: bash

   gcloud components update

More information on the GCP SDK can be found at
`https://cloud.google.com/sdk/gcloud/reference
<https://cloud.google.com/sdk/gcloud/reference>`_.

Docker
------

Applications and services for the Pitt-Google-Broker are deployed to the
cloud as docker images. You will need to have docker
installed on your system to build and deploy these images. See
`the official Docker install guide <https://docs.docker.com/install/>`_ for
more details.

Git
---

Git is a version control system used to manage and track changes to project source code.
It is also the recommended method for retrieving project source code. Please see
the `Git installation guide <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`_
for installation instructions.
