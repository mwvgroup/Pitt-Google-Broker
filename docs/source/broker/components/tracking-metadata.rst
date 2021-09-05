Tracking Metadata
==================

The broker uses Pub/Sub message attributes to track metadata for provenance and
performance benchmarking.

Each morning, night conductor processes the Pub/Sub "counter" subscriptions,
collects the metadata, and stores it in the metadata BigQuery table.
See the script at broker/night_conductor/end_night/process_pubsub_counters.py.

Currently, the collected metadata includes the publish timestamp of each message, and
information about the Avro file storage and the survey's originating Kafka stream.

To track additional metadata:

1. Add desired information to a custom attribute(s) on the appropriate Pub/Sub message.
   Note, the message's publish timestamp is automatically attached; it does not need
   to be added manually.

2. If this is a new Pub/Sub stream, add the topic/subscription to the resource names in
   the processing script at broker/night_conductor/end_night/process_pubsub_counters.py.

3. Add the corresponding column(s) to the schema template(s) for the metadata table(s)
   in broker/setup_broker/templates/.
   The column name(s) will be: the name(s) of the attribute(s) plus
   the name stub of the publishing topic, separated by a double underscore.
   If this is a new Pub/Sub stream, remember to add a column for the publish timestamp.
