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
from google.cloud.exceptions import PreconditionFailed

from broker_utils import gcp_utils
from broker_utils.schema_maps import load_schema_map
from broker_utils.types import AlertFilename, AlertIds
from exceptions import SchemaParsingError


PROJECT_ID = os.getenv('GCP_PROJECT')
TESTID = os.getenv('TESTID')
SURVEY = os.getenv('SURVEY')
VERSIONTAG = os.getenv("VERSIONTAG")

schema_dir_name = "schema_maps"
schema_file_name = f"{SURVEY}.yaml"
path_to_local_schema_yaml = Path(__file__).resolve().parent / f"{schema_dir_name}/{schema_file_name}"
schema_map = load_schema_map(SURVEY, TESTID, schema=path_to_local_schema_yaml)

# connect to the cloud logger
logging_client = logging.Client()
log_name = 'ps-to-gcs-cloudfnc'
logger = logging_client.logger(log_name)

# GCP resources used in this module
bucket_name = f"{PROJECT_ID}-{SURVEY}_alerts_{VERSIONTAG}"  # store the Avro files
ps_topic = f"{SURVEY}-alerts"
if TESTID != "False":
    bucket_name = f'{bucket_name}-{TESTID}'
    ps_topic = f'{ps_topic}-{TESTID}'

client = storage.Client()
bucket = client.get_bucket(client.bucket(bucket_name, user_project=PROJECT_ID))

# By default, spool data in memory to avoid IO unless data is too big
# LSST alerts are anticipated at 80 kB, so 1000 kB should be plenty
max_alert_packet_size = 1_000_000


class TempAlertFile(SpooledTemporaryFile):
    """Subclass of SpooledTemporaryFile that is tied into the log

    Log warning is issued when file rolls over onto disk.
    """

    def rollover(self) -> None:
        """Move contents of the spooled file from memory onto disk"""
        msg = f'Alert size exceeded max memory size: {self._max_size}'
        logger.log_text(msg, severity="WARNING")
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
    """ Entry point for the Cloud Function

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
    try:
        upload_bytes_to_bucket(msg, context)
    # this is raised by blob.upload_from_file if the object already exists in the bucket
    except PreconditionFailed:
        # we'll simply return, and the duplicate alert will go no further in our pipeline
        return


def upload_bytes_to_bucket(msg, context) -> None:
    """Uploads the msg data bytes to a GCP storage bucket. Prior to storage,
    corrects the schema header to be compliant with BigQuery's strict
    validation standards if the alert is from a survey version with an
    associated pickle file in the valid_schemas directory.
    """

    data = base64.b64decode(msg['data'])  # alert packet, bytes
    attributes = msg['attributes']
    # Get the survey name and version
    # survey = guess_schema_survey(data)

    with TempAlertFile(max_size=max_alert_packet_size, mode='w+b') as temp_file:
        temp_file.write(data)
        temp_file.seek(0)

        alert = extract_alert_dict(temp_file)
        temp_file.seek(0)
        alert_ids = AlertIds(schema_map, alert_dict=alert[0])

        filename = AlertFilename(
            {
                "objectId": alert_ids.objectId,
                "sourceId": alert_ids.sourceId,
                "topic": attributes.get("kafka.topic", "no_topic"),
                "format": "avro",
            }
        ).name

        if SURVEY == 'ztf':
            fix_schema(temp_file, alert, data, filename)
        temp_file.seek(0)

        blob = bucket.blob(filename)
        blob.metadata = create_file_metadata(alert, context, alert_ids)

        # raise a PreconditionFailed exception if filename already exists in the bucket using "if_generation_match=0"
        # let it raise. the main function will catch it and then drop the message.
        blob.upload_from_file(temp_file, if_generation_match=0)

        # Cloud Storage says this is not a duplicate, so now we publish the broker's main "alerts" stream
        temp_file.seek(0)
        gcp_utils.publish_pubsub(
            ps_topic,
            temp_file.read(),
            attrs={
                str(alert_ids.id_keys.objectId): str(alert_ids.objectId),
                str(alert_ids.id_keys.sourceId): str(alert_ids.sourceId),
                **attributes,
            }
        )


def create_file_metadata(alert, context, alert_ids):
    """Return key/value pairs to be attached to the file as metadata."""
    metadata = {'file_origin_message_id': context.event_id}
    metadata[alert_ids.id_keys.objectId] = alert_ids.objectId
    metadata[alert_ids.id_keys.sourceId] = alert_ids.sourceId
    metadata['ra'] = alert[0][schema_map['source']]['ra']
    metadata['dec'] = alert[0][schema_map['source']]['dec']
    return metadata


def extract_alert_dict(temp_file):
    """Extracts and returns the alert data as a dict wrapped in a list.
    """
    # load the file and get the data with fastavro
    temp_file.seek(0)
    alert = [r for r in fastavro.reader(temp_file)]
    return alert


def fix_schema(temp_file, alert, data, filename):
    """ Rewrites the temp_file with a corrected schema header
        so that it is valid for upload to BigQuery.

    Args:
        temp_file: Temporary file containing the alert.
    """
    version = guess_schema_version(data)

    # get the corrected schema if it exists, else return
    try:
        fpkl = f'valid_schemas/{SURVEY}_v{version}.pkl'
        inpath = Path(__file__).resolve().parent / fpkl
        with inpath.open('rb') as infile:
            valid_schema = pickle.load(infile)

    except FileNotFoundError:
        return

    # write the corrected file
    temp_file.seek(0)
    fastavro.writer(temp_file, valid_schema, alert)
    temp_file.truncate()  # removes leftover data
    temp_file.seek(0)


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
        err_msg = f'Could not guess schema version for alert {alert_bytes}'
        logger.log_text(err_msg, severity='ERROR')
        raise SchemaParsingError(err_msg)

    return version_match.group(2).decode()


# mock data and run the module
if __name__ == "__main__":
    from broker_utils.testing import Mock
    mock = Mock(schema_map=schema_map, drop_cutouts=False, serialize="avro")
    args = mock.cfinput
    run(args.msg, args.context)

    print(mock.my_test_alert.ids)
