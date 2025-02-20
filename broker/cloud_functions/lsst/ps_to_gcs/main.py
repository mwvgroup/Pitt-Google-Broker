#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores the alert data as an Avro file in Cloud Storage."""

import base64
import io
import json
import os
import struct
from typing import Optional

import fastavro
import pittgoogle
from confluent_kafka.schema_registry import SchemaRegistryClient
from google.cloud import functions_v1, logging, storage, pubsub_v1
from google.cloud.exceptions import PreconditionFailed


PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")
VERSIONTAG = os.getenv("VERSIONTAG")

# connect to the cloud logger and publisher
logging_client = logging.Client()
log_name = "ps-to-gcs-cloudfnc"
logger = logging_client.logger(log_name)
publisher = pubsub_v1.PublisherClient()

# GCP resources used in this module
client = storage.Client()
available_schemas = {
    "7.1": "v7_1",
    "7.2": "v7_2",
    "7.3": "v7_3",
}
ALERTS_TOPIC = pittgoogle.Topic.from_cloud(
    "alerts", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

# alerts are stored in GCS buckets based on their schema version; alerts in topic may contain multiple schema versions.
# to avoid making the get_bucket call for each alert, we'll cache the buckets and assign the correct bucket dynamically
# based on the alert's schema version
BUCKETS = {}
for versiontag in available_schemas.values():
    bucket_name = f"{PROJECT_ID}-{SURVEY}_alerts_{versiontag}"
    if TESTID != "False":
        bucket_name = f"{bucket_name}-{TESTID}"
    BUCKETS[versiontag] = client.get_bucket(client.bucket(bucket_name, user_project=PROJECT_ID))

# define a binary data structure for packing and unpacking bytes
_ConfluentWireFormatHeader = struct.Struct(">bi")


def run(event: dict, context: functions_v1.context.Context) -> None:
    """Entry point for the Cloud Function

    For args descriptions, see:
    https://cloud.google.com/functions/docs/writing/background#function_parameters

    Args:
        event: Pub/Sub message data and attributes.
            `data` field contains the message data in a base64-encoded string.
            `attributes` field contains the message's custom attributes in a dict.

        context: The Cloud Function's event metadata.
            It has the following attributes:
                `event_id`: the Pub/Sub message ID.
                `timestamp`: the Pub/Sub message publish time.
                `event_type`: for example: "google.pubsub.topic.publish".
                `resource`: the resource that emitted the event.
    """
    try:
        upload_bytes_to_bucket(event, context)
    # this is raised by blob.upload_from_file if the object already exists in the bucket
    except PreconditionFailed:
        # we'll simply pass, and the duplicate alert will go no further in our pipeline
        pass


def upload_bytes_to_bucket(event: dict, context: functions_v1.context.Context) -> None:
    """Uploads the msg data bytes to a GCP storage bucket."""

    alert_bytes = base64.b64decode(event["data"])  # alert packet, bytes
    attributes = event.get("attributes", {})

    # unpack the alert and read schema ID
    header_bytes = alert_bytes[:5]
    schema_id = deserialize_confluent_wire_header(header_bytes)

    # get and load schema
    sr_client = SchemaRegistryClient({"url": "https://usdf-alert-schemas-dev.slac.stanford.edu"})
    schema = sr_client.get_schema(schema_id=schema_id)
    parse_schema = json.loads(schema.schema_str)
    schema_version = parse_schema["namespace"].split(".")[1]
    content_bytes = io.BytesIO(alert_bytes[5:])

    # deserialize the alert and create Alert object
    alert_dict = fastavro.schemaless_reader(content_bytes, parse_schema)
    filename = generate_alert_filename(
        {
            "objectId": alert_dict["diaObject"]["diaObjectId"],
            "sourceId": alert_dict["diaSource"]["diaSourceId"],
            "topic": attributes.get("kafka.topic", "no_topic"),
            "format": "avro",
        }
    )

    # get bucket based on the alert's schema version and store the Avro file
    bucket = BUCKETS.get(schema_version)
    blob = bucket.blob(filename)
    blob.metadata = create_file_metadata(alert_dict, context)

    # raise a PreconditionFailed exception if filename already exists in the bucket using "if_generation_match=0"
    # let it raise. the main function will catch it and then drop the message.
    blob.upload_from_file(io.BytesIO(alert_bytes), if_generation_match=0)

    # Cloud Storage says this is not a duplicate, so now we publish the broker's main "alerts" stream
    return publish_outgoing_alert(
        topic_name=ALERTS_TOPIC.name,
        message=alert_bytes,
        attributes={
            "diaObjectId": str(alert_dict["diaObject"]["diaObjectId"]),
            "diaSourceId": str(alert_dict["diaSource"]["diaSourceId"]),
            "schema_version": schema_version,
            **attributes,
        },
    )


def deserialize_confluent_wire_header(raw):
    """Parses the byte prefix for Confluent Wire Format-style Kafka messages.
    Parameters
    ----------
    raw : `bytes`
        The 5-byte encoded message prefix.
    Returns
    -------
    schema_version : `int`
        A version number which indicates the Confluent Schema Registry ID
        number of the Avro schema used to encode the message that follows this
        header.
    """
    _, version = _ConfluentWireFormatHeader.unpack(raw)

    return version


def generate_alert_filename(aname: dict) -> str:
    """
    Generate the filename of an alert stored to a Cloud Storage bucket.

    Args:
        aname:
            Components to create the filename. Required key/value pairs are those needed to create a parsed filename.
            Extra keys are ignored.

    Returns:
        str: The formatted filename as "{topic}/{objectId}/{sourceId}.{format}".
    """
    topic = aname.get("topic", "no_topic")
    object_id = aname.get("objectId")
    source_id = aname.get("sourceId")
    file_format = aname.get("format", "avro")

    return f"{topic}/{object_id}/{source_id}.{file_format}"


def create_file_metadata(alert_dict: dict, context):
    """Return key/value pairs to be attached to the file as metadata."""
    metadata = {"file_origin_message_id": context.event_id}
    metadata["diaObjectId"] = alert_dict["diaObject"]["diaObjectId"]
    metadata["diaSourceId"] = alert_dict["diaSource"]["diaSourceId"]
    metadata["ra"] = alert_dict["diaSource"]["ra"]
    metadata["dec"] = alert_dict["diaSource"]["dec"]
    return metadata


def publish_outgoing_alert(
    topic_name: str, message: bytes, attributes: Optional[dict] = None
) -> str:
    """Publish messages to a Pub/Sub topic."""

    # enforce bytes type for message
    if not isinstance(message, bytes):
        raise TypeError("`message` must be bytes.")

    topic_path = publisher.topic_path(PROJECT_ID, topic_name)
    future = publisher.publish(topic_path, data=message, **attributes)

    return future.result()
