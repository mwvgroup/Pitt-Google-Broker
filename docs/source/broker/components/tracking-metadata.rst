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

2. Add the corresponding column(s) to the schema template(s) for the metadata table(s)
   in broker/setup_broker/templates/.
   The format for a column name must be: the name of the attribute plus
   the name stub of the publishing topic, separated by a double underscore.
   If this is a new Pub/Sub stream, remember to add a column for the publish timestamp.

3. If this is a new Pub/Sub stream:

    - Attach a "counter" subscription to the new topic. The subscription name stub
      should have the form `<topic_name_stub>-counter`.

    - Add the topic name stub to the resource names at the top of the processing script
      at broker/night_conductor/end_night/process_pubsub_counters.py.
      The script will automatically process the subscription and collect all
      attributes for which there is a corresponding column in the BigQuery table.
