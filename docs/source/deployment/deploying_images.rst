Deploying Docker Images to GCP
==============================

Individual broker instances are deployed to the cloud as dedicated docker images
and then stored using the
`Container Registry  <https://cloud.google.com/container-registry>`_
service. In general, these images requires two files:

1. A DockerFile that configures the broker's runtime environment.
2. A python script that is executed when the runtime environment is launched.

Copies of these files are bundled with the broker source code under the
*docker_files/* directory and can be downloaded from the official
`GitHub Repository`_, or by using ``git``:

.. code-block:: bash

   git clone https://github.com/mwvgroup/Pitt-Google-Broker

Building an Image
-----------------

The first step to deploying a Docker image is to build it from the
corresponding Dockerfile. This is accomplished by using the `build` command:

.. code-block:: bash

   sudo docker build -t [IMAGE NAME] -f [DOCKERFILE NAME] [DIRECTORY PATH OF DOCKERFILE]

Next the docker image needs to be tagged with the name of the GCP
Container Registry associated with your project. The tag name is a combination
of the Container Registry host name, your project Id, and the image name.
For those unfamiliar with host names, the `gcr.io` host is recommended:

.. code-block:: bash

   sudo docker tag [IMAGE NAME] [HOSTNAME]/[PROJECT-ID]/[IMAGE NAME]:[VERSION]

The version number can be chosen arbitrarily, however it is strongly recommended
to choose a consistent versioning scheme. If working within a version controlled
project, the recommended solution is to version images using the hash value of the
most recent commit for that file. This hash value can be retrieved as follows:

.. code-block:: bash

    git log -1 --format=format:"%H" [DOCKERFILE NAME]


Uploading an Image
------------------

.. important:: The container registry automatically creates storage buckets
   to store uploaded images. This means you must have ``Storage Admin``
   permissions in order to upload new images.

Images can be uploaded to the cloud using the ``docker`` command line utility
as follows:

.. code-block:: bash

   docker push [HOSTNAME]/[PROJECT-ID]/[IMAGE]

For more information on pushing to the GCP Container Registry, see
`here <https://cloud.google.com/container-registry/docs/pushing-and-pulling>`_.


.. _docker_files: https://github.com/mwvgroup/Pitt-Google-Broker/tree/master/docker_files
.. _GitHub Repository: https://github.com/mwvgroup/Pitt-Google-Broker