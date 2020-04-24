Deploying Docker Images to GCP
==============================

Individual PGB services are deployed to the cloud as dedicated docker images. The Dockerfiles that define these images are stored in the PGB [GitHub Repository](https://github.com/mwvgroup/Pitt-Google-Broker) under the ``docker_files`` directory. Each Dockerfile has a corresponding script in the same directory that launches a particular PGB service when the docker container is deployed.

In the following steps we will configure GCP to store the built images for these Dockerfiles in the GCP Container Registry. This allows for easy  deployment of the images and their corresponding PGB services to various GCP products.


Uploading an Image
------------------

The first step to deploying a Docker image is to build it from the
corresponding Dockerfile. This is accomplished by using the `build` command:

.. code-block:: bash

   docker build -t [IMAGE NAME] -f [DOCKERFILE NAME] [DIRECTORY PATH OF DOCKERFILE]

Next the docker image needs to be tagged with the name of the GCP
Container Registry associated with your project. The tag name is a combination
of the Container Registry host name (e.g., `gcr.io`), your project Id, and the
image name:

.. code-block:: bash

   docker tag [IMAGENAME] [HOSTNAME]/[PROJECT-ID]/[IMAGENAME]

Finally, the image is pushed up to the cloud:

.. code-block:: bash

   docker push [HOSTNAME]/[PROJECT-ID]/[IMAGE]

For more information on pushing to the GCP Container Registry, see
`here <https://cloud.google.com/container-registry/docs/pushing-and-pulling>`_.

Configuring Automatic Image Deployment
--------------------------------------

List steps here on how to automatically deploy Docker Images to GCP products.

