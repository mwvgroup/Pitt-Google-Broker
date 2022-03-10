# Cloud Run Services for Component Tests

This directory contains source code for the Cloud Run services that facilitate component tests, including:

- bucket_to_pubsub: Service that pulls files from a Cloud Storage bucket and publishes them to a Pub/Sub topic, one message per file. The bucket, Pub/Sub topic, and publish format (Avro or JSON) are configurable via the Pub/Sub message used to trigger the service.

- verify_pubsub: Service that verifies messages in its (Pub/Sub) trigger topic by checking that message:

  - attributes contain the expected keys
  - payload is formatted in the expected way
  - payload contains the expected keys

## Build container images and push to the registry

This only needs to be done once per GCP project.
The component-test Workflow will automatically deploy a service using the registry image.
