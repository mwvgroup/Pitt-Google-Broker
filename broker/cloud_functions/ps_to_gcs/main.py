#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module is intended to be deployed as a
Google Cloud Function with a Pub/Sub trigger.
It will listen to the Pub/Sub stream containing the original alert packet
and store each alert as an Avro file in Cloud Storage.
See
https://cloud.google.com/functions/docs/tutorials/pubsub#functions-prepare-environment-python
for a tutorial.
"""

from google.cloud import logging
from google.cloud import storage
import base64
import re
from pathlib import Path
from tempfile import SpooledTemporaryFile
import pickle
import fastavro


# connect to the cloud logger
logging_client = logging.Client()
log_name = 'ps-to-gcs-cloudfnc'
logger = logging_client.logger(log_name)

# bucket to store the Avro files
bucket_name = 'ardent-cycling-243415_ztf_alert_avro_bucket'
storage_client = storage.Client()
bucket = storage_client.get_bucket(bucket_name)

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

def upload_ztf_bytes_to_bucket(msg, context) -> None:
    """Uploads the msg data bytes to a GCP storage bucket. Prior to storage,
    corrects the schema header to be compliant with BigQuery's strict
    validation standards if the alert is from a survey version with an
    associated pickle file in the valid_schemas directory.

    Args:
        msg (dict): Pub/Sub message. `data` field contains the alert.
             `attributes` field contains custom attributes.
        context (google.cloud.functions.Context): The Cloud Functions event
         metadata. The `event_id` field contains the Pub/Sub message ID. The
         `timestamp` field contains the publish time.
    """

    data = base64.b64decode(msg['data'])  # alert packet, bytes
    atrs = msg['attributes']  # custom attributes
    filename = f"{atrs['kafka.topic']}_{atrs['kafka.timestamp']}.avro"

    blob = bucket.blob(filename)

    # Get the survey name and version
    survey = guess_schema_survey(data)
    version = guess_schema_version(data)

    # By default, spool data in memory to avoid IO unless data is too big
    # LSST alerts are anticipated at 80 kB, so 150 kB should be plenty
    max_alert_packet_size = 150000
    with TempAlertFile(max_size=max_alert_packet_size, mode='w+b') as temp_file:
        temp_file.write(data)
        temp_file.seek(0)
        fix_schema(temp_file, survey, version, filename)
        blob.upload_from_file(temp_file)
        logger.log_text(f'Uploaded {filename} to {bucket.name}')


def fix_schema(temp_file, survey, version, filename):
    """ Rewrites the temp_file with a corrected schema header
        so that it is valid for upload to BigQuery.

    Args:
        temp_file: Temporary file containing the alert.
        survey: Name of the survey generating the alert.
        version: Schema version.
    """

    # get the corrected schema if it exists, else return
    try:
        fpkl = f'valid_schemas/{survey}_v{version}.pkl'
        inpath = Path(__file__).resolve().parent / fpkl
        with inpath.open('rb') as infile:
            valid_schema = pickle.load(infile)

    except FileNotFoundError:
        msg = f'Original schema header retained for {survey} v{version}; file {filename}'
        logger.log_text(msg)
        return

    # load the file and get the data with fastavro
    temp_file.seek(0)
    data = [r for r in fastavro.reader(temp_file)]

    # write the corrected file
    temp_file.seek(0)
    fastavro.writer(temp_file, valid_schema, data)
    temp_file.truncate()  # removes leftover data
    temp_file.seek(0)

    logger.log_text(f'Schema header reformatted for {survey} v{version}; file {filename}')

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

def guess_schema_survey(alert_bytes: bytes) -> str:
    """Retrieve the ZTF schema version

    Args:
        alert_bytes: An alert from ZTF or LSST

    Returns:
        The survey name
    """

    survey_regex_pattern = b'("namespace":\s")(\S*)(")'
    survey_match = re.search(survey_regex_pattern, alert_bytes)
    if survey_match is None:
        err_msg = f'Could not guess survey name for alert {alert_bytes}'
        logger.log_text(err_msg, severity='ERROR')
        raise SchemaParsingError(err_msg)

    return survey_match.group(2).decode()

class CloudConnectionError(Exception):
    """Error connecting to one or more Google Cloud services"""
    pass

class SchemaParsingError(Exception):
    """Error parsing or guessing properties of an alert schema"""
    pass
