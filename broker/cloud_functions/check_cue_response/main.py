#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module checks whether the broker responded appropriately to the
auto-scheduler's cue. If it has not, a message(s) is logged with
`severity = 'CRITICAL'` which triggers a GCP alerting policy.
"""

import base64
import os
import time

from google.cloud import logging
from googleapiclient import discovery

PROJECT_ID = os.getenv('GCP_PROJECT')
TESTID = os.getenv('TESTID')
SURVEY = os.getenv('SURVEY')
ZONE = os.getenv('ZONE')

compute_service = discovery.build('compute', 'v1')

# connect to the logger
logging_client = logging.Client()
log_name = 'check-cue-response-cloudfnc'  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
consumer = f'{SURVEY}-consumer'  # vm
night_conductor = f'{SURVEY}-night-conductor'  # vm
if TESTID != "False":
    consumer = f'{consumer}-{TESTID}'
    night_conductor = f'{night_conductor}-{TESTID}'


def run(msg, context) -> None:
    """ Entry point for the Cloud Function
    Args:
        msg (dict): Pub/Sub message.

                    `data` field (bytes) contains the message data. It is
                    expected to be one of ['START', 'END'].

                    `attributes` field (dict) contains the message's custom
                    attributes.
        context (google.cloud.functions.Context): The Cloud Functions event
            metadata. The `event_id` field contains the Pub/Sub message ID. The
            `timestamp` field contains the publish time.
    """
    cue = base64.b64decode(msg['data']).decode('utf-8')  # 'START' or 'END'
    attrs = msg['attributes']  # dict

    continue_checks = check_cue_value(cue)  # check that cue is an expected value
    if continue_checks:  # do the checks
        check_cue_response(cue, attrs)


def check_cue_value(cue):
    # check that the cue is an expected value and log result
    expected_values = ['START', 'END']

    if cue in expected_values:
        continue_checks = True
        msg = (f'Broker instance with keywords [{SURVEY},{TESTID}] received '
               f'cue = {cue}. Giving the broker time to '
               'respond, then will check its response to the cue.'
               )
        severity = 'INFO'
    else:
        continue_checks = False
        msg = (f'Broker received cue = {cue}, which is an unexpected value. '
               'The broker is not expected to respond. No further checks will be done.')
        severity = 'CRITICAL'
    logger.log_text(msg, severity=severity)

    return continue_checks


def check_cue_response(cue, attrs):
    """Check that the broker components responded appropriately to the cue.
    """
    # check that consumer has started or stopped, as appropriate
    check_consumer(cue, attrs)

    # check that night conductor has started
    if cue == "END":
        _ = check_night_conductor()


def check_night_conductor():
    # night-conductor should start in response to either cue
    request_kwargs = {
        'project': PROJECT_ID,
        'zone': ZONE,
        'instance': night_conductor
    }
    status, metadata = get_vm_info(request_kwargs)

    # check and log the status
    if status == 'RUNNING':
        msg = f'{night_conductor} is running as expected'
        severity = 'INFO'
    else:
        msg = f'{night_conductor} should be running, but its status = {status}'
        severity = 'CRITICAL'
    logger.log_text(msg, severity=severity)

    # in the future, may want to check the metadata as well

    return (status, metadata)


def check_consumer(cue, attrs):
    request_kwargs = {
        'project': PROJECT_ID,
        'zone': ZONE,
        'instance': consumer
    }
    status, metadata = get_vm_info(request_kwargs)

    # determine if we expect the consumer to be running
    expect_consumer_running = True
    if (attrs is not None) and ('KAFKA_TOPIC' in attrs.keys()):
        if attrs['KAFKA_TOPIC'] == 'NONE':
            expect_consumer_running = False

    if cue == 'START':
        # check and log the status
        if status == 'RUNNING':
            if expect_consumer_running:
                msg = f'{consumer} is running as expected'
                severity = 'INFO'
            else:
                msg = f'{consumer} is running, but this is unexpected since KAFKA_TOPIC==NONE'
                severity = 'DEBUG'

        else:
            if expect_consumer_running:
                msg = f'{consumer} should be running, but its status = {status}'
                severity = 'CRITICAL'
            else:
                msg = f'{consumer} is not running; this is expected since KAFKA_TOPIC==NONE'
                severity = 'INFO'

        logger.log_text(msg, severity=severity)

    elif cue == 'END':
        # check and log the status
        if status == 'TERMINATED':
            msg = f'{consumer} has stopped as expected'
            severity = 'INFO'
        else:
            msg = f'{consumer} should have stopped, but its status = {status}'
            severity = 'CRITICAL'
        logger.log_text(msg, severity=severity)


def get_vm_info(request_kwargs):
    request = compute_service.instances().get(**request_kwargs)
    response = request.execute()  # dict

    status = response['status']
    metadata = response['metadata']

    return (status, metadata)
