# Component Tests

This directory contains all files needed to run the tests described below.

## Objective

Test that each component responds to its trigger (usually a Pub/Sub stream) is correctly integrated with the broker's data resources:

- Pub/Sub (component's trigger topic and output topic(s))
- BigQuery (output table(s))
- Cloud Storage (output bucket(s)), and runs successfully end-to-end when messages are published to the component's trigger topic (Pub/Sub).

## Steps

1. Send Input: Publish a fixed set of messages to the component's trigger topic (Pub/Sub stream).

1. Component Processing (we are testing that this happens automatically, as expected): The component should accept the messages, process them, and write output data to Pub/Sub, BigQuery, and/or Cloud Storage)

1. Check Output: Check the relevant Pub/Sub, BigQuery, and/or Cloud Storage resources for the output data. Validate that it is as expected.
