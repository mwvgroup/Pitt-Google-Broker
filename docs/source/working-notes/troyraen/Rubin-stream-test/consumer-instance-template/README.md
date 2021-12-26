# Create a Compute Engine instance template for the Consumer VM

Trigger Cloud Build to create a Compute Engine instance template for the
Consumer VM (with the Kafka -> Pub/Sub connector):

```bash
gcloud builds submit --config cloudbuild.yaml
```

This proceeds in 3 steps:

1. Build the container image from the Dockerfile in this directory
2. Push the image to the Container Registry
3. Create an instance template from the container

## Reference links

- https://cloud.google.com/sdk/gcloud/reference/compute/instance-templates/create-with-container
