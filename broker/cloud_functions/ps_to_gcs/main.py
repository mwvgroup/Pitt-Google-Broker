#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores the alert data as an Avro file in Cloud Storage,
fixing the schema first, if necessary.
"""

import base64
import os
import pickle
import re
from pathlib import Path
from tempfile import SpooledTemporaryFile

import fastavro
from google.cloud import logging
from google.cloud import storage

from broker_utils import schema_maps
from exceptions import SchemaParsingError

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)
storage_client = storage.Client()

# connect to the cloud logger
logging_client = logging.Client()
log_name = "ps-to-gcs-cloudfnc"
logger = logging_client.logger(log_name)

# GCP resources used in this module
bucket_name = f"{PROJECT_ID}-{SURVEY}-alert_avros"  # store the Avro files
if TESTID != "False":
    bucket_name = f"{bucket_name}-{TESTID}"
# connect to the avro bucket
bucket = storage_client.get_bucket(bucket_name)

# By default, spool data in memory to avoid IO unless data is too big
# LSST alerts are anticipated at 80 kB, so 150 kB should be plenty
max_alert_packet_size = 150000


class TempAlertFile(SpooledTemporaryFile):
    """Subclass of SpooledTemporaryFile that is tied into the log

    Log warning is issued when file rolls over onto disk.
    """

    def rollover(self) -> None:
        """Move contents of the spooled file from memory onto disk"""

        log.warning(f"Alert size exceeded max memory size: {self._max_size}")
        super().rollover()

    @property
    def readable(self):
        return self._file.readable

    @property
    def writable(self):
        return self._file.writable

    @property
    def seekable(self):  # necessary so that fastavro can write to the file
        return self._file.seekable


def run(msg, context) -> None:
    """Entry point for the Cloud Function

    For args descriptions, see:
    https://cloud.google.com/functions/docs/writing/background#function_parameters

    Args:
        msg: Pub/Sub message data and attributes.
            `data` field contains the message data in a base64-encoded string.
            `attributes` field contains the message's custom attributes in a dict.

        context: The Cloud Function's event metadata.
            It has the following attributes:
                `event_id`: the Pub/Sub message ID.
                `timestamp`: the Pub/Sub message publish time.
                `event_type`: for example: "google.pubsub.topic.publish".
                `resource`: the resource that emitted the event.
    """
    upload_bytes_to_bucket(msg, context)


def upload_bytes_to_bucket(msg, context) -> None:
    """Uploads the msg data bytes to a GCP storage bucket. Prior to storage,
    corrects the schema header to be compliant with BigQuery's strict
    validation standards if the alert is from a survey version with an
    associated pickle file in the valid_schemas directory.
    """

    data = base64.b64decode(msg["data"])  # alert packet, bytes
    attributes = msg["attributes"]
    # Get the survey name and version
    # survey = guess_schema_survey(data)

    with TempAlertFile(max_size=max_alert_packet_size, mode="w+b") as temp_file:
        temp_file.write(data)
        temp_file.seek(0)

        alert = extract_alert_dict(temp_file)
        temp_file.seek(0)
        filename = create_filename(alert, attributes)
        if SURVEY == "ztf":
            fix_schema(temp_file, alert, data, filename)
        temp_file.seek(0)

        blob = bucket.blob(filename)
        blob.upload_from_file(temp_file)
        attach_file_metadata(blob, alert, context)  # must be after file upload

    logger.log_text(f"Uploaded {filename} to {bucket.name}")


def attach_file_metadata(blob, alert, context):
    metadata = {"file_origin_message_id": context.event_id}
    metadata["objectId"] = alert[0]["objectId"]
    metadata["candid"] = alert[0]["candid"]
    metadata["ra"] = alert[0][schema_map["source"]]["ra"]
    metadata["dec"] = alert[0][schema_map["source"]]["dec"]
    blob.metadata = metadata
    blob.patch()


def create_filename(alert, attributes):
    # alert is a single alert dict wrapped in a list
    oid = alert[0][schema_map["objectId"]]
    sid = alert[0][schema_map["source"]][schema_map["sourceId"]]
    topic = attributes["kafka.topic"]
    filename = f"{oid}.{sid}.{topic}.avro"
    return filename


def extract_alert_dict(temp_file):
    """Extracts and returns the alert data as a dict wrapped in a list."""
    # load the file and get the data with fastavro
    temp_file.seek(0)
    alert = [r for r in fastavro.reader(temp_file)]
    return alert


def fix_schema(temp_file, alert, data, filename):
    """Rewrites the temp_file with a corrected schema header
        so that it is valid for upload to BigQuery.

    Args:
        temp_file: Temporary file containing the alert.
    """
    version = guess_schema_version(data)

    # get the corrected schema if it exists, else return
    try:
        fpkl = f"valid_schemas/{SURVEY}_v{version}.pkl"
        inpath = Path(__file__).resolve().parent / fpkl
        with inpath.open("rb") as infile:
            valid_schema = pickle.load(infile)

    except FileNotFoundError:
        msg = (
            f"Original schema header retained for {SURVEY} v{version}; file {filename}"
        )
        logger.log_text(msg)
        return

    # write the corrected file
    temp_file.seek(0)
    fastavro.writer(temp_file, valid_schema, alert)
    temp_file.truncate()  # removes leftover data
    temp_file.seek(0)

    logger.log_text(
        f"Schema header reformatted for {SURVEY} v{version}; file {filename}"
    )


def guess_schema_version(alert_bytes: bytes) -> str:
    """Retrieve the ZTF schema version

    Args:
        alert_bytes: An alert from ZTF or LSST

    Returns:
        The schema version
    """

    version_regex_pattern = b'("version":\s")([0-9]*\.[0-9]*)(")'
    version_match = re.search(version_regex_pattern, alert_bytes)
    if version_match is None:
        err_msg = f"Could not guess schema version for alert {alert_bytes}"
        logger.log_text(err_msg, severity="ERROR")
        raise SchemaParsingError(err_msg)

    return version_match.group(2).decode()
