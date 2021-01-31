#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
""" Simulate the ztf-consumer by publishing alerts to a Pub/Sub topic.
"""

import os
import time
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1

import pub_sub_client.message_service as psms

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

def publish_stream(alertRate, runTime):

    publish_batch_every = (5, 'sec')
    pbe = publish_batch_every  # shorthand

    # get number of alerts to publish per batch
    pubN = get_batch_rate(alertRate, publish_batch_every=pbe)   # int

    # get number of iterations to run
    Nbatches = convert_runTime_to_Nbatches()

    # 

def convert_runTime_to_Nbatches(runTime, ):
    rt = convert_time_to_publish_unit()

def convert_time_to_publish_unit(runTime, publish_unit='sec'):
    """
    Args:
        runTime (int, str): (number, unit) to convert to publish_unit
        publish_unit (str): time units consumer will use for publish rate

    Returns:
        runTime converted to publish_unit
    """

    rtN, rtU = runTime
    
    # convert the time to (N, 'sec')
    if publish_unit == 'sec':
        if rtU == 'sec':
            converted_runTime = rtN
        if rtU == 'min':
            converted_runTime = rtN*60
        if rtU == 'hr':
            converted_runTime = rtN*3600
        if rtU == 'night':
            converted_runTime = rtN*10*3600

    else:
        msg = f"received publish_units='{publish_unit}', but only configured for publish_unit='sec'"
        raise ValueError(msg)

    return converted_runTime

def get_batch_rate(alertRate, publish_batch_every=(5,'sec')):
    """ Find the number of alerts to publish per batch
    """

    # if user requested 1 batch, return their number
    if (type(alertRate)==tuple) and (alertRate[1]=='once'):
        batch_rate = alertRate[0]

    # else convert to batch rate
    else:
        pbeN, pbeU = publish_batch_every
        alertRate = convert_rate_strings(alertRate)  #tuple
        avg_publish_rate = convert_rate_to_publish_unit(alertRate, publish_unit=pbeU)  # float
        batch_rate = get_batch_rate_from_avg(avg_publish_rate, pbeN)  # int, per batch

    return batch_rate

def get_batch_rate_from_avg(avg_publish_rate, publish_interval):
    return int(avg_publish_rate*publish_interval)

def convert_rate_to_publish_unit(alertRate, publish_unit='sec'):
    """
    Args:
        alertRate (int, str): (number, unit) to convert to publish_unit
        publish_unit (str): time units consumer will use for publish rate

    Returns:
        alerts_per_unit (float): alertRate in units per publish_unit
    """

    arN, arU = alertRate
    
    # convert the rate to (N, 'perSec')
    if publish_unit == 'sec':
        if arU == 'perSec':
            alerts_per_unit = arN
        if arU == 'perMin':
            alerts_per_unit = arN/60
        if arU == 'perHr':
            alerts_per_unit = arN/3600
        if arU == 'perNight':
            alerts_per_unit = arN/10/3600

    else:
        msg = f"received publish_units='{publish_unit}', but only configured for publish_unit='sec'"
        raise ValueError(msg)

    return alerts_per_unit

def convert_rate_strings(alertRate):

    if type(alertRate)!=str:
        aRate = alertRate
    
    elif alertRate=='ztf-active-avg':
        aRate = (250000, 'perNight')

    else:
        msg = f"'ztf-active-avg' is the only string currently configured for the alertRate"
        raise ValueError

    return aRate



def old():
    timeout = 50.0
    testid='test'
    topic_name = 'troy_test_topic'

    max_alerts = 1
    Nmax=400
    rate = Nmax # alerts/min
    waitsec = 1/(rate/60)

    subscription_id = 'ztf_alert_data_subtest'
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)


    # msglist = psms.subscribe_alerts(subscription_id, max_alerts=1, decode=True)
    # does not work


    response = subscriber.pull(
        request={
            "subscription": subscription_path,
            "max_messages": max_alerts,
        }
    )

    for msg in response.received_messages:
        print("Received message.data type:", type(msg.message.data))

    ack_ids = [msg.ack_id for msg in response.received_messages]

    subscriber.acknowledge(
        request={
            "subscription": subscription_path,
            "ack_ids": ack_ids,
        }
    )

    # nack a message
    ack_deadline_seconds = 0
    subscriber.modify_ack_deadline(
        request={
            "subscription": subscription_path,
            "ack_ids": ack_ids,
            "ack_deadline_seconds": ack_deadline_seconds,
        }
    )



    i=0
    def callback(message):
        try:
            publish_message(message)
        except:
            raise
        else:
            message.ack()

    def publish_message(message):
        global i
        try:
            psms.publish_pubsub(topic_name, message.data)
        except:
            raise
        else:
            i = i+1
            print(f'{i} message published')#, waiting {waitsec} seconds to ack')
            if i==Nmax:
                raise NameError('Nmax exceeded')
            # time.sleep(waitsec)



    # Limit the subscriber to only have ten outstanding messages at a time.
    flow_control = pubsub_v1.types.FlowControl(max_messages=100)

    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=callback, flow_control=flow_control
    )
    print(f"Listening for messages on {subscription_path}..\n")

    # Wrap subscriber in a 'with' block to automatically call close() when runTimee.
    with subscriber:
        try:
            # When `timeout` is not set, result() will block indefinitely,
            # unless an exception is encountered first.
            streaming_pull_future.result(timeout=timeout)
        except TimeoutError:
            print('timeout')
            streaming_pull_future.cancel()
        except KeyboardInterrupt:
            print('keyboard')
            streaming_pull_future.cancel()
        except NameError:
            print('name')
            streaming_pull_future.cancel()
