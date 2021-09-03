Tracking Metadata
==================

The broker uses Pub/Sub message attributes to track metadata for provenance and
performance benchmarking.

Each morning, night conductor processes the Pub/Sub "counter" subscriptions,
collects the metadata, and stores it in the metadata BigQuery table.
See the script at broker/night_conductor/end_night/process_pubsub_counters.py.
(todo: move this to broker_utils).

Currently, the collected metadata includes the publish time of each message, and
information about the original Kafka stream and the Avro file storage.

To track additional metadata:

1. Add the information to a custom attribute(s) on the appropriate Pub/Sub message.

2. Add the Pub/Sub topic and subscription to the resource names in
   broker/night_conductor/end_night/process_pubsub_counters.py.

3. Add a corresponding column to the schema of the metadata BigQuery table.
   The column name(s) will be: the name(s) of the custom attribute(s) from step 1 plus
   the name stub of the publishing topic, separated by a double underscore.
