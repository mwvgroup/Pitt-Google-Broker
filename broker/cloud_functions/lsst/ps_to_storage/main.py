#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores LSST alert data as an Avro file in Cloud Storage."""

import base64
import io
import json
import os
import struct
from typing import Optional
from astropy.time import Time

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
log_name = "ps-to-storage-cloudfnc"
logger = logging_client.logger(log_name)
publisher = pubsub_v1.PublisherClient()

# GCP resources used in this module
ALERTS_TOPIC = pittgoogle.Topic.from_cloud(
    "alerts", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
TOPIC_BIGQUERY_IMPORT = pittgoogle.Topic.from_cloud(
    "bigquery-import", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
bucket_name = f"{PROJECT_ID}-{SURVEY}_alerts"
if TESTID != "False":
    bucket_name = f"{bucket_name}-{TESTID}"

client = storage.Client()
bucket = client.get_bucket(client.bucket(bucket_name, user_project=PROJECT_ID))

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
        store_alert_data(event, context)
    # this is raised by blob.upload_from_file if the object already exists in the bucket
    except PreconditionFailed:
        # we'll simply pass, and the duplicate alert will go no further in our pipeline
        pass


def store_alert_data(event: dict, context: functions_v1.context.Context) -> None:
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
            "schema_version": schema_version,
            "objectId": alert_dict["diaObject"]["diaObjectId"],
            "sourceId": alert_dict["diaSource"]["diaSourceId"],
            "alert_date": alert_dict["diaSource"]["midpointMjdTai"],
            "format": "avro",
        }
    )

    blob = bucket.blob(filename)
    blob.metadata = create_file_metadata(alert_dict, context)

    # raise a PreconditionFailed exception if filename already exists in the bucket using "if_generation_match=0"
    # let it raise. the main function will catch it and then drop the message.
    blob.upload_from_file(io.BytesIO(alert_bytes), if_generation_match=0)

    # Cloud Storage says this is not a duplicate, so now we publish the broker's main "alerts" stream
    publish_alerts_stream(
        topic_name=ALERTS_TOPIC.name,
        message=alert_bytes,
        attributes={
            "diaObjectId": str(alert_dict["diaObject"]["diaObjectId"]),
            "diaSourceId": str(alert_dict["diaSource"]["diaSourceId"]),
            "schema_version": schema_version,
            **attributes,
        },
    )

    # publish the alert as a JSON message to the bigquery-import topic
    TOPIC_BIGQUERY_IMPORT.publish(_create_valid_json(alert_dict, attributes))

    return


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
        str: The formatted filename as "{schema_version}/{YYYY-MM-DD}/{objectId}/{sourceId}.{format}".
    """

    schema_version = aname["schema_version"]
    alert_date = aname["alert_date"]
    object_id = aname["objectId"]
    source_id = aname["sourceId"]
    file_format = aname["format"]

    # convert the MJD timestamp to "YYYY-MM-DD"
    time_obj = Time(alert_date, format="mjd")
    date_string = time_obj.datetime.strftime("%Y-%m-%d")

    return f"{schema_version}/{date_string}/{object_id}/{source_id}.{file_format}"


def create_file_metadata(alert_dict: dict, context):
    """Return key/value pairs to be attached to the file as metadata."""

    metadata = {"file_origin_message_id": context.event_id}
    metadata["diaObjectId"] = alert_dict["diaObject"]["diaObjectId"]
    metadata["diaSourceId"] = alert_dict["diaSource"]["diaSourceId"]
    metadata["ra"] = alert_dict["diaSource"]["ra"]
    metadata["dec"] = alert_dict["diaSource"]["dec"]

    return metadata


def publish_alerts_stream(
    topic_name: str, message: bytes, attributes: Optional[dict] = None
) -> str:
    """Publish original alert bytes to a Pub/Sub topic."""

    # enforce bytes type for message
    if not isinstance(message, bytes):
        raise TypeError("`message` must be bytes.")

    topic_path = publisher.topic_path(PROJECT_ID, topic_name)
    future = publisher.publish(topic_path, data=message, **attributes)

    return future.result()


def _create_valid_json(alert_dict: dict, attributes: dict) -> pittgoogle.alert.Alert:
    """Transforms alert data to a valid JSON message."""

    # define and remove cutouts from message
    cutouts = [
        "cutoutTemplate",
        "cutoutScience",
        "cutoutDifference",
    ]
    for key in cutouts:
        alert_dict.pop(key, None)

    # replace NaN values with None
    valid_json = _transform_nan_to_none(alert_dict)

    return pittgoogle.Alert.from_dict(payload=valid_json, attributes=attributes)


def _transform_nan_to_none(alert_dict: dict) -> dict:
    """Recursively replace NaN values with None in a dictionary."""

    # convert NaN to None
    if isinstance(alert_dict, dict):
        return {k: _transform_nan_to_none(v) for k, v in alert_dict.items()}
    if isinstance(alert_dict, list):
        return [_transform_nan_to_none(v) for v in alert_dict]
    if isinstance(alert_dict, float) and math.isnan(alert_dict):
        return None

    return alert_dict
