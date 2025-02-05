#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module publishes alert data to a Pub/Sub topic."""

import base64
import fastavro
import io
import json
import os
import pittgoogle
import struct
from confluent_kafka.schema_registry import SchemaRegistryClient
from google.cloud import functions_v1, pubsub_v1, logging

PROJECT_ID = os.getenv("GCP_PROJECT")
SURVEY = os.getenv("SURVEY")
TESTID = os.getenv("TESTID")
VERSIONTAG = os.getenv("VERSIONTAG")

# connect to the cloud logger
log_name = "store-bigquery-cloudfnc"  # same log for all broker instances
logging_client = logging.Client()
logger = logging_client.logger(log_name)

# GCP resources used in this module
ALERT_DATA_TOPIC = pittgoogle.Topic.from_cloud(
    "alert-data", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

# define a binary data structure for packing and unpacking bytes
_ConfluentWireFormatHeader = struct.Struct(">bi")


def run(event: dict, _context: functions_v1.context.Context) -> None:
    """Send alert data to various Pub/Sub topics.

    Args:
        event: Pub/Sub message data and attributes.
            `data` field contains the message data in a base64-encoded string.
            `attributes` field contains the message's custom attributes in a dict.

        context: Metadata describing the Cloud Function's trigging event.

    'context' is an unused argument in the function that is required
    see https://cloud.google.com/functions/1stgendocs/writing/write-event-driven-functions#background-functions
    """

    # decode the base64-encoded message data
    decoded_data = base64.b64decode(event["data"])
    attrs = event.get("attributes", {})

    # unpack the alert
    alert_bytes = decoded_data
    header_bytes = alert_bytes[:5]

    # deserialize the alert
    schema_id = deserialize_confluent_wire_header(header_bytes)

    # get and load schema
    sr_client = SchemaRegistryClient({"url": "https://usdf-alert-schemas-dev.slac.stanford.edu"})
    schema = sr_client.get_schema(schema_id=schema_id)
    latest_schema = json.loads(schema.schema_str)
    content_bytes = io.BytesIO(alert_bytes[5:])

    # create alert object
    alert_dict = fastavro.schemaless_reader(content_bytes, latest_schema)
    # alert = pittgoogle.Alert.from_dict(msg=alert_dict, schema_name="lsst")
    alert = pittgoogle.Alert.from_dict(payload=alert_dict, attributes=attrs)

    # transform the data and publish it to Pub/Sub
    ALERT_DATA_TOPIC.publish(_drop_cutouts(alert))


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


def _drop_cutouts(alert: pittgoogle.alert.Alert) -> pittgoogle.alert.Alert:
    """Removes cutouts from alerts."""
    # collect attributes
    attrs = {**alert.attributes}

    # define message
    msg = alert.dict

    # define and remove cutouts from message
    cutouts = ["cutoutTemplate", "cutoutScience", "cutoutDifference"]
    for key in cutouts:
        msg.pop(key, None)

    # create outgoing alert
    alert_out = pittgoogle.Alert.from_dict(payload=msg, attributes=attrs)

    return alert_out
