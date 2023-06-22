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

from broker_utils.avro_schemas.load import load_all_schemas
from broker_utils.schema_maps import load_schema_map, get_key
from broker_utils.types import AlertFilename, AlertIds
from exceptions import SchemaParsingError


PROJECT_ID = os.getenv('GCP_PROJECT')
TESTID = os.getenv('TESTID')
SURVEY = os.getenv('SURVEY')
BROKER_VERSION = os.getenv("BROKER_VERSION")
BROKER_NAME = "Pitt-Google"

schema_in = load_all_schemas()["elasticc.v0_9_1.alert.avsc"]
schema_map = load_schema_map(SURVEY, TESTID)
sobjectId, ssourceId = get_key("objectId", schema_map), get_key("sourceId", schema_map)
# connect to the cloud logger
logging_client = logging.Client()
log_name = 'ps-to-gcs-cloudfnc'
logger = logging_client.logger(log_name)

# GCP resources used in this module
bucket_name = f'{PROJECT_ID}-{SURVEY}-alert_avros'  # store the Avro files
if TESTID != "False":
    bucket_name = f'{bucket_name}-{TESTID}'
bucket = storage.Client().get_bucket(bucket_name)

# By default, spool data in memory to avoid IO unless data is too big
# LSST alerts are anticipated at 80 kB, so 150 kB should be plenty
max_alert_packet_size = 150000


class TempAlertFile(SpooledTemporaryFile):
    """Subclass of SpooledTemporaryFile that is tied into the log

    Log warning is issued when file rolls over onto disk.
    """

    def rollover(self) -> None:
        """Move contents of the spooled file from memory onto disk"""

        log.warning(f'Alert size exceeded max memory size: {self._max_size}')
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
    # PreconditionFailed is raised by blob.upload_from_file if the object already exists in the bucket
    except PreconditionFailed:
        # we're done with it. we simply return
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
        blob.metadata = create_file_metadata(alert, context, attributes, alert_ids)
        # raise PreconditionFailed exception if filename already exists in the bucket using "if_generation_match=0".
        # let it raise. the main function will handle it.
        blob.upload_from_file(temp_file, if_generation_match=0)



def create_file_metadata(alert, context, attributes, alert_ids):
    """Return key/value pairs to be attached to the file as metadata."""
    return {
        "broker_name": BROKER_NAME,
        "broker_version": BROKER_VERSION,
        "broker_ingest_timestamp": context.event_id,
        "kafka_topic": attributes["kafka.topic"],
        "kafka_timestamp": attributes["kafka.timestamp"],
        "alertId": alert[0]["alertId"],
        alert_ids.id_keys.objectId: alert_ids.objectId,
        alert_ids.id_keys.sourceId: alert_ids.sourceId,
        "ra": alert[0][schema_map['source']][schema_map['ra']],
        "dec": alert[0][schema_map['source']][schema_map['dec']],
    }


def extract_alert_dict(temp_file):
    """Extract and return the alert data as a dict wrapped in a list."""
    temp_file.seek(0)
    return [fastavro.schemaless_reader(temp_file, schema_in)]


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
