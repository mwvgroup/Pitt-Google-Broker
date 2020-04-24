Developer Dependencies
======================

This section outlines installation instructions for various project
dependencies. You can choose to install all dependencies at once, or revisit
the included subsections as needed.

Google Cloud SDK
----------------

You will need to have the ``gcloud`` command line API installed to handle
authentication tasks when connecting and deploying services to GCP. Up to
date installation instructions are available at
`https://cloud.google.com/sdk/install <https://cloud.google.com/sdk/install>`_.
After installation is finished, ensure that ``gcloud`` is available in the
system ``PATH``. If you already have ``gcloud`` installed, ensure that is is
up to date using:

.. code-block:: bash

   gcloud components update

To authenticate your command line installation, use the ``auth`` command:

.. code-block:: bash
   gcloud auth login
   gcloud config set project [PROJECT-ID]

You will also need to authorize Docker to push images to the GCP Container
Registry where your Docker images will be stored. This is achieved by using
the command:

.. code-block:: bash

   gcloud auth configure-docker


More information on the GCP SDK can be found at 
`https://cloud.google.com/sdk/gcloud/reference 
<https://cloud.google.com/sdk/gcloud/reference>`_

Travis
------

The travis command line tool is necessary for configuring Google Could
authentication with continuous integration on 
`travis-ci.com <https://www.travis-ci.com/>`_. 
The travis command line tool can be installed using:

.. code-block:: bash

   sudo gem install travis

Certain versions of Mac OSX include System Integrity Protection (SIP) which 
effects the installation of packages that use the default Ruby install 
(including `travis`). If using OS X El Capitan or later, you may need to 
install the commandline tool using:

.. code-block:: bash

   sudo gem install -n /usr/local/bin/ travis

Once `travis` is installed, login to your user account.

.. code-block:: bash

   travis login --pro

Docker
------

Applications and services for the Pitt-Google-Broker are deployed to the
Google Cloud Platform (GCP) as docker images. You will need to have docker
installed on your system to build and deploy these images. See
`the official Docker install guide <https://docs.docker.com/install/>`_ for
more details.
