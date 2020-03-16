# Deploying a Broker Instance

This document outline how to deploy a version of the Pitt-Google Broker (PGB)
to the Google Cloud Platform (GCP). It is intended as a reference for
developers interested in deploying their own dedicated or down-stream broker
system on GCP, or for those who would simply like to better understand the PGB
pipeline. 

Before proceeding with installation, you will need to create and
authenticate a new GCP project. This project, and it's unique Id, will be
used to organize the various resources used by the deployed broker. For
information on creating a new GCP project, see: 
[https://cloud.google.com/resource-manager/docs/creating-managing-projects](https://cloud.google.com/resource-manager/docs/creating-managing-projects).

## Dependencies

### Docker

Applications and services for the Pitt-Google-Broker are deployed to the
Google Cloud Platform (GCP) as docker images. You will need to have docker
installed on your system to build and deploy these images. See
[https://docs.docker.com/install/](https://docs.docker.com/install/) for
more details.

### Google Cloud SDK

You will need to have the `gcloud` command line API installed to handle
authentication tasks when connecting and deploying services to GCP. Up to 
date installation instructions are available at 
[https://cloud.google.com/sdk/install](https://cloud.google.com/sdk/install). 
After installation is finished, ensure that ``gcloud`` is available in the 
system ``PATH``.

To authenticate your command line installation, use the ``auth`` command:

```bash
gcloud auth login
```  

You will also need to authorize Docker to push images to the GCP Container
Registry where your Docker images will be stored. This is achieved by using
the command:

```bash
gcloud auth configure-docker
```

More information on the GCP SDK can be found at 
[https://cloud.google.com/sdk/gcloud/reference](https://cloud.google.com/sdk/gcloud/reference). 

# Deploying Docker Images to GCP

Individual PGB services are deployed to the cloud as dedicated docker images.
The Dockerfiles that define these images are stored in the PGB
[GitHub Repository](https://github.com/mwvgroup/Pitt-Google-Broker) under
the ``docker_files`` directory. Each Dockerfile has a corresponding script
in the same directory that launches a particular PGB service when the
docker container is deployed. 

In the following steps we will configure GCP to store the built images for
these Dockerfiles in the GCP Container Registry. This allows for easy 
deployment of the images and their corresponding PGB services to various GCP
products.

## Uploading an Image

The first step to deploying a Docker image is to build it from the
corresponding Dockerfile. This is accomplished by using the `build` command:

```bash
docker build -t [IMAGE NAME] -f [DOCKERFILE NAME] [DIRECTORY PATH OF DOCKERFILE]
```

Next the docker image needs to be tagged with the name of the GCP
Container Registry associated with your project. The tag name is a combination
of the Container Registry host name (e.g., `gcr.io`), your project Id, and the
image name:

```bash
docker tag [IMAGENAME] [HOSTNAME]/[PROJECT-ID]/[IMAGENAME]
```

Finally, the image is pushed up to the cloud:

```bash
docker push [HOSTNAME]/[PROJECT-ID]/[IMAGE]
```

For more information on pushing to the GCP Container Registry, see 
[https://cloud.google.com/container-registry/docs/pushing-and-pulling](https://cloud.google.com/container-registry/docs/pushing-and-pulling).

## Configuring Automatic Image Deployment

List steps here on how to automatically deploy Docker Images to GCP products.

# Deploying the Alert Consumer

## Configure Cloud Functions

## Deploy the Consumer Image


