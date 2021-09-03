#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module is part of the broker's auto-scheduler.
It sets metadata attributes on the night conductor VM and starts it.
"""

import base64
from datetime import datetime
from google.cloud import logging
from googleapiclient import discovery
import os

from broker_utils import schema_maps


PROJECT_ID = os.getenv('GCP_PROJECT')
TESTID = os.getenv('TESTID')
SURVEY = os.getenv('SURVEY')
ZONE = os.getenv('ZONE')

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)

# this script would be much simpler if we could use gcloud on the cmd line,
# but cloud fnc environments appear not to have the CLI tools.
# so we have to use the REST API
service = discovery.build('compute', 'v1')

# connect to the logger
logging_client = logging.Client()
log_name = 'cue-night-conductor-cloudfnc'  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
instance_name = f'{SURVEY}-night-conductor'
if TESTID != "False":
    instance_name = f'{instance_name}-{TESTID}'

def run(msg, context) -> None:
    """ Entry point for the Cloud Function
    Args:
        msg (dict): Pub/Sub message.

                    `data` field (bytes) contains the message data. It is
                    expected to be one of ['START', 'END'].

                    `attributes` field (dict) contains the message's custom
                    attributes. Currently used to set the KAFKA_TOPIC and is
                    expected to contain one key from
                    ['topic_date', 'KAFKA_TOPIC']. If neither are present,
                    'topic_date' will be set to the current UTC date.

        context (google.cloud.functions.Context): The Cloud Functions event
         metadata. The `event_id` field contains the Pub/Sub message ID. The
         `timestamp` field contains the publish time.
    """
    cue = base64.b64decode(msg['data']).decode('utf-8')  # str
    attrs = msg['attributes']  # dict

    continue_cue = check_cue_value(cue, attrs)  # check that cue is an expected value
    if continue_cue:
        cue_night_conductor(cue, attrs)

def check_cue_value(cue, attrs):
    # check that the cue is an expected value and log the result
    expected_values = ['START','END']
    if cue in expected_values:
        continue_cue = True
        msg = (f'cloud fnc with keywords [{SURVEY}, {TESTID}] received '
            f'cue = {cue}; attrs = {attrs}. Cueing night-conductor.'
        )
        severity = 'INFO'
    else:
        continue_cue = False
        msg = (f'Valid cues are {expected_values}, but '
            f'cloud fnc with keywords [{SURVEY}, {TESTID}] received cue = {cue}. Exiting.'
        )
        severity = 'CRITICAL'
    logger.log_text(msg, severity=severity)

    return continue_cue

def cue_night_conductor(cue, attrs):
    """Sets appropriate metadata attributes on the night-conductor VM and starts it.
    Args:
        cue (str): One of 'START' or 'END'. Whether to start or end the broker's night.
        attrs (dict): Used to determine the topic to be ingested.
                      Expect empty dict or one key of ['topic_date', 'KAFKA_TOPIC']
    """
    request_kwargs = {
        'project': PROJECT_ID,
        'zone': ZONE,
        'instance': instance_name
    }

    update_items = get_update_items(cue, attrs)
    update_keys = [ui['key'] for ui in update_items]
    fingerprint, keep_items = get_current_metadata(update_keys, request_kwargs)
    metadata = {
        'fingerprint': fingerprint,
        'items': update_items + keep_items,
    }
    set_metadata(metadata, request_kwargs)
    set_machine_type(cue, request_kwargs)
    start_vm(request_kwargs)

def get_update_items(cue, attrs):
    """Metadata items to update.
    """
    update_items = [{'key': 'NIGHT', 'value': cue}]
    if cue == 'START':
        update_items.append({'key': 'KAFKA_TOPIC', 'value': get_kafka_topic(attrs)})
    return update_items

def get_kafka_topic(attrs):
    # If a specific topic or date was reqested in the attrs, set it.
    # otherwise, set topic for today's date UTC
    TOPIC_SYNTAX = schema_map['TOPIC_SYNTAX']
    replace = 'yyyymmdd'
    set_today = False

    if attrs is None:
        set_today = True

    elif 'KAFKA_TOPIC' in attrs.keys():
        KAFKA_TOPIC = attrs['KAFKA_TOPIC']

    elif 'topic_date' in attrs.keys():
        KAFKA_TOPIC = TOPIC_SYNTAX.replace(replace, attrs['topic_date'])

    else:
        set_today = True

    if set_today:
        yyyymmdd = datetime.utcnow().strftime("%Y%m%d")
        KAFKA_TOPIC = TOPIC_SYNTAX.replace(replace, yyyymmdd)

    # log the topic
    msg = f'cloud fnc with keywords [{SURVEY}, {TESTID}] will set KAFKA_TOPIC={KAFKA_TOPIC}'
    logger.log_text(msg, severity='INFO')

    return KAFKA_TOPIC

def get_current_metadata(update_keys, request_kwargs):
    # get the current metadata and fingerprint
    request = service.instances().get(**request_kwargs)
    response = request.execute()  # dict
    fingerprint = response['metadata']['fingerprint']
    current_items = response['metadata']['items']
    keep_items = [dic for dic in current_items if dic['key'] not in update_keys]

    return (fingerprint, keep_items)

def set_metadata(metadata, request_kwargs):
    """Set attributes on night-conductor
    """
    request = service.instances().setMetadata(**request_kwargs, body=metadata)
    response = request.execute()

def set_machine_type(cue, request_kwargs):
    """Set the machine size according to the expected load.

    See also
    https://cloud.google.com/compute/docs/reference/rest/v1/instances/setMachineType
    https://cloud.google.com/compute/docs/machine-types
    https://cloud.google.com/compute/docs/instances/creating-instance-with-custom-machine-type
    """
    # decide on a machine type
    machine_type_stub = f"zones/{ZONE}/machineTypes"
    if cue == "Start":
        # night conductor does no processing, it just starts other things
        # set smallest machine size possible
        request_body = {"machineType": "/".join([machine_type_stub, "f1-micro"])}
    elif cue == "End":
        # night conductor processes pubsub streams for metadata.
        # a "small", shared-core machine with 4GB memory can handle largest ZTF night
        memMB = 4 * 1024
        custom_type = f"e2-custom-small-{memMB}"
        request_body = {"machineType": "/".join([machine_type_stub, custom_type])}

    # set machine type
    request = service.instances().setMachineType(body=request_body, **request_kwargs)
    response = request.execute()

    # check for errors
    # I (Troy) am confused about the result of the following test:
    # If the machine is off, this works.
    # If the machine is on, I expect it to generate an error,
    # but it neither changes the machine type nor generates an error.
    # I don't understand why.
    # I think we are supposed to be able to access errors like this:
    if "error" in response.keys():
        logger.log_text(response["error"].errors, severity="DEBUG")



def start_vm(request_kwargs):
    # start the vm
    request = service.instances().start(**request_kwargs)
    response = request.execute()
