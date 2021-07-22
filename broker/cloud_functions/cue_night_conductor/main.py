#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module is part of the broker's auto-scheduler.
It sets metadata attributes on the night conductor VM and starts it.
"""

import base64
from datetime import datetime
from googleapiclient import discovery
import os


PROJECT_ID = os.getenv('GCP_PROJECT')
TESTID = os.getenv('TESTID')
SURVEY = os.getenv('SURVEY')
ZONE = os.getenv('ZONE')

# GCP resources used in this module
instance_name = f'{SURVEY}-night-conductor'
if TESTID != "False":
    instance_name = f'{instance_name}-{TESTID}'

service = discovery.build('compute', 'v1')

def run(msg, context) -> None:
    """ Entry point for the Cloud Function
    Args:
        msg (dict): Pub/Sub message. `data` field contains the message data.
             `attributes` field contains custom attributes.
        context (google.cloud.functions.Context): The Cloud Functions event
         metadata. The `event_id` field contains the Pub/Sub message ID. The
         `timestamp` field contains the publish time.
    """
    cue = base64.b64decode(msg['data']).decode('utf-8')  # 'START' or 'END'
    cue_night_conductor(cue)

def cue_night_conductor(cue):
    """Sets appropriate metadata attributes on the night-conductor VM and starts it.
    Args:
        cue (str): One of 'START' or 'END'. Whether to start or end the broker's night.
    """
    request_kwargs = {
        'project': PROJECT_ID,
        'zone': ZONE,
        'instance': instance_name
    }

    update_items = get_update_items(cue)
    update_keys = [ui['key'] for ui in update_items]
    fingerprint, keep_items = get_current_metadata(update_keys, request_kwargs)
    metadata = {
        'fingerprint': fingerprint,
        'items': update_items + keep_items,
    }
    set_metadata(metadata, request_kwargs)
    start_vm(request_kwargs)

def get_update_items(cue):
    """Metadata items to update.
    """
    update_items = [{'key': 'NIGHT', 'value': cue}]
    if cue == 'START':
        update_items.append({'key': 'KAFKA_TOPIC', 'value': get_kafka_topic()})
    return update_items

def get_kafka_topic():
    yyyymmdd = datetime.utcnow().strftime("%Y%m%d")
    KAFKA_TOPIC = f'ztf_{yyyymmdd}_programid1'
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

def start_vm(request_kwargs):
    # start the vm
    request = service.instances().start(**request_kwargs)
    response = request.execute()
