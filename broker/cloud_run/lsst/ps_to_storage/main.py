#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores LSST alert data as an Avro file in Cloud Storage."""

import base64
import io
import json
import math
import os
import struct
from typing import Any, Dict, Optional
from astropy.time import Time

import flask
import fastavro
import pittgoogle
from confluent_kafka.schema_registry import SchemaRegistryClient
from google.cloud import logging, storage
from google.cloud.exceptions import PreconditionFailed

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
logging.Client().setup_logging()

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match deploy.sh

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# GCP resources used in this module
TOPIC_ALERTS = pittgoogle.Topic.from_cloud(
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
publisher = pittgoogle.Topic.client

# define a binary data structure for packing and unpacking bytes
_ConfluentWireFormatHeader = struct.Struct(">bi")
sr_client = SchemaRegistryClient({"url": "https://usdf-alert-schemas-dev.slac.stanford.edu"})

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Uploads alert data to a GCS bucket. Publishes a de-duplicated "alerts" stream (${survey}-alerts) containing the
    original alert bytes and publishes an additional JSON message stream (${survey}-bigquery-import) in which a
    BigQuery subscription is used to write alert data to the appropriate BigQuery table.

    This module is intended to be deployed as a Cloud Run service. It will operate as an HTTP endpoint
    triggered by Pub/Sub messages. This function will be called once for every message sent to this route.
    It should accept the incoming HTTP request and return a response.

    Returns
    -------
    response : tuple(str, int)
        Tuple containing the response body (string) and HTTP status code (int). Flask will convert the
        tuple into a proper HTTP response. Note that the response is a status message for the web server.
    """

    # extract the envelope from the request that triggered the endpoint
    # this contains a single Pub/Sub message with the alert to be processed
    envelope = flask.request.get_json()

    try:
        store_alert_data(envelope)
    # this is raised by blob.upload_from_file if the object already exists in the bucket
    except PreconditionFailed:
        # we'll simply pass, and the duplicate alert will go no further in our pipeline
        pass

    return "", HTTP_204


def store_alert_data(envelope) -> None:
    """Uploads the msg data bytes to a GCP storage bucket."""

    alert_bytes = base64.b64decode(envelope["message"]["data"])  # alert packet, bytes
    attributes = envelope["message"].get("attributes", {})

    # unpack the alert and read schema ID
    header_bytes = alert_bytes[:5]
    schema_id = deserialize_confluent_wire_header(header_bytes)

    # get and load schema
    schema = sr_client.get_schema(schema_id=schema_id)
    parse_schema = json.loads(schema.schema_str)
    schema_version = parse_schema["namespace"].split(".")[1]
    content_bytes = io.BytesIO(alert_bytes[5:])

    # deserialize the alert
    alert_dict = fastavro.schemaless_reader(content_bytes, parse_schema)

    # convert the MJD timestamp to "YYYY-MM-DD"
    time_obj = Time(alert_dict["diaSource"]["midpointMjdTai"], format="mjd")
    alert_date = time_obj.datetime.strftime("%Y-%m-%d")

    filename = generate_alert_filename(
        {
            "schema_version": schema_version,
            "alert_date": alert_date,
            "objectId": alert_dict["diaObject"]["diaObjectId"],
            "sourceId": alert_dict["diaSource"]["diaSourceId"],
            "format": "avro",
        }
    )

    blob = bucket.blob(filename)
    blob.metadata = create_file_metadata(alert_dict, event_id=envelope["message"]["messageId"])

    # raise a PreconditionFailed exception if filename already exists in the bucket using "if_generation_match=0"
    # let it raise. the main function will catch it and then drop the message.
    blob.upload_from_string(alert_bytes, if_generation_match=0)

    # Cloud Storage says this is not a duplicate, so now we publish the broker's main "alerts" stream
    publish_alerts_stream(
        topic_name=TOPIC_ALERTS.name,
        message=alert_bytes,
        attributes={
            "diaObjectId": str(alert_dict["diaObject"]["diaObjectId"]),
            "diaSourceId": str(alert_dict["diaSource"]["diaSourceId"]),
            "schema_version": schema_version,
            **attributes,
        },
    )

    # publish the alert as a JSON message to the bigquery-import topic
    TOPIC_BIGQUERY_IMPORT.publish(
        _reformat_alert_data_to_valid_json(
            alert_dict, attributes={"schema_version": schema_version}
        )
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
        str: The formatted filename as "{schema_version}/{YYYY-MM-DD}/{objectId}/{sourceId}.{format}".
    """

    schema_version = aname["schema_version"]
    alert_date = aname["alert_date"]
    object_id = aname["objectId"]
    source_id = aname["sourceId"]
    file_format = aname["format"]

    return f"{schema_version}/{alert_date}/{object_id}/{source_id}.{file_format}"


def create_file_metadata(alert_dict: dict, event_id: str) -> dict:
    """Return key/value pairs to be attached to the file as metadata."""

    metadata = {"file_origin_message_id": event_id}
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


def _reformat_alert_data_to_valid_json(
    alert_dict: dict, attributes: dict
) -> pittgoogle.alert.Alert:
    """Creates an Alert object whose data will be published as a valid JSON message."""

    # cutouts are sent as bytes; define and remove them
    cutouts = [
        "cutoutTemplate",
        "cutoutScience",
        "cutoutDifference",
    ]
    for key in cutouts:
        alert_dict.pop(key, None)

    # alert may contain NaN values; replace them with None
    valid_json_dict = _reformat_nan_in_alert_dict(alert_dict)

    return pittgoogle.Alert.from_dict(payload=valid_json_dict, attributes=attributes)


def _reformat_nan_in_alert_dict(alert_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively replace NaN values with None if present in alert dictionary."""
    return {k: _replace_nan_values_with_none(v) for k, v in alert_dict.items()}


def _replace_nan_values_with_none(value: Any) -> Any:
    """Recursively replace NaN values with None."""
    if isinstance(value, dict):
        return {k: _replace_nan_values_with_none(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_nan_values_with_none(v) for v in value]
    if isinstance(value, float) and math.isnan(value):
        return None
    return value
