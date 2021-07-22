#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module checks whether the broker responded appropriately to the
auto-scheduler's cue. If it has not, a message(s) is logged with
`severity = 'CRITICAL'` which triggers a GCP alerting policy.
"""

import base64
from google.cloud import logging
from googleapiclient import discovery
import os
import time


PROJECT_ID = os.getenv('GCP_PROJECT')
TESTID = os.getenv('TESTID')
SURVEY = os.getenv('SURVEY')
ZONE = os.getenv('ZONE')

# connect to the logger
logging_client = logging.Client()
log_name = 'check-cue-response-cloudfnc'  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
consumer = f'{SURVEY}-consumer'  # vm
night_conductor = f'{SURVEY}-night-conductor'  # vm
bq_sink = f'{SURVEY}-bq-sink'  # dataflow job
value_added = f'{SURVEY}-value-added'  # dataflow job
if TESTID != "False":
    consumer = f'{consumer}-{TESTID}'
    night_conductor = f'{night_conductor}-{TESTID}'
    bq_sink = f'{bq_sink}-{TESTID}'
    value_added = f'{value_added}-{TESTID}'

compute_service = discovery.build('compute', 'v1')
dataflow_service = discovery.build('dataflow', 'v1b3')


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
    continue_checks = check_cue_value(cue)  # check that cue is an expected value
    if continue_checks:  # do the checks
        check_cue_response(cue)

def check_cue_value(cue):
    # check that the cue is an expected value and log result
    expected_values = ['START','END']

    if cue in expected_values:
        msg = (f'Broker instance with keywords [{SURVEY},{TESTID}] received '
        f'cue = {cue}. Giving the broker time to '
        'respond, then will check its response to the cue.'
        )
        severity = 'INFO'
    else:
        msg = (f'Broker received cue = {cue}, which is an unexpected value. '
        'The broker is not expected to respond. No further checks will be done.')
        severity = 'CRITICAL'
    logger.log_text(msg, severity=severity)

    continue_checks = True if severity =='INFO' else False
    return continue_checks

def check_cue_response(cue):
    """Check that the broker components responded appropriately to the cue.
    """
    # sleep so night-conductor has time to boot, then check it
    time.sleep(30)
    status, metadata = check_night_conductor()

    # sleep so the rest of the broker has time to respond
    time.sleep(7*60)  # 7 min. Draining Dataflow jobs takes the longest

    # finish the checks
    check_dataflow(cue, metadata)
    check_consumer(cue)

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

def check_dataflow(cue, metadata):
    """Check that the jobs are either running or drained
    """
    expected_jobs = [bq_sink, value_added]

    # get the job IDs
    # if cue == 'END', the job IDs have been deleted from the metadata by now,
    # so we must use the old metadata
    # if cue == 'START', the job IDs would not have been set in the
    # metadata earlier, so we must get the new values now.
    if cue == 'START':
        request_kwargs = {
            'project': PROJECT_ID,
            'zone': ZONE,
            'instance': night_conductor
        }
        __, metadata = get_vm_info(request_kwargs)
    jobids = get_dataflow_jobids(metadata)  # list of job IDs

    # get the current states
    job_states = {}  # {job name: current state}}
    for jobid in jobids:
        region = '-'.join(ZONE.split('-')[:-1])
        kwargs = {'projectId':PROJECT_ID, 'location':region, 'jobId':jobid}
        request = dataflow_service.projects().locations().jobs().get(**kwargs)
        state = request.execute()
        job_states[state['name']] = state['currentState']

    if cue == 'START':
        # check that both the value-added and bq-sink jobs are running
        for job_name in expected_jobs:
            if job_name in job_states.keys():
                # job exists. check the status
                status = job_states[job_name]
                if status == 'JOB_STATE_RUNNING':
                    msg = f'{job_name} Dataflow job is running as expected.'
                    severity = 'INFO'
                else:
                    msg = (f'{job_name} Dataflow job exists, but it is not '
                    'running as expected. Its status is {}'
                    )
                    severity = 'CRITICAL'
            else:
                # job does not exist or didn't get recorded properly
                msg = (f'{job_name} Dataflow job should be running, but it either '
                    'did not start or its job ID did not get recorded in '
                    'night-conductor metadata.'
                )
                severity = 'CRITICAL'
            logger.log_text(msg, severity=severity)
    else:
        # check that the jobs have stopped and drained
        for job_name, state in job_states.items():
            if state == 'JOB_STATE_DRAINED':
                msg = f'{job_name} drained as expected.'
                severity = 'INFO'
            else:
                msg = f'{job_name} should have drained, but its status is {state}.'
                severity = 'CRITICAL'
            logger.log_text(msg, severity=severity)

def get_dataflow_jobids(metadata):
    for item in metadata['items']:
        if item['key'] == 'RUNNING_BEAM_JOBS':
            jobid_string = item['value']
    jobids = jobid_string.split(' ')  # list of job ids
    return jobids

def check_consumer(cue):
    request_kwargs = {
        'project': PROJECT_ID,
        'zone': ZONE,
        'instance': consumer
    }
    status, metadata = get_vm_info(request_kwargs)

    if cue == 'START':
        # check and log the status
        if status == 'RUNNING':
            msg = f'{consumer} is running as expected'
            severity = 'INFO'
        else:
            msg = f'{consumer} should be running, but its status = {status}'
            severity = 'CRITICAL'
        logger.log_text(msg, severity=severity)

        # in the future, may want to check the metadata as well

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
