#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
""" Simulate the ztf-consumer by publishing alerts to a Pub/Sub topic.
"""

from concurrent.futures import TimeoutError
from google.cloud import pubsub
import os
import sys
import time
from warnings import warn

import pub_sub_client.message_service as psms

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')


def publish_stream(
    testid, alertRate, runTime=None, publish_batch_every=(5,'sec'), sub_id=None, topic_id=None, nack=False):
    """
    Args:
        testid (str): testid of the broker testing instance
        alertRate (tuple(int, str)): desired rate at which alerts will be published (e.g., (100, 'perMin'))
        runTime (tuple(int, str)): desired length of time simulator runs for (e.g., (5, 'hr'))
        publish_batch_every (tuple(int, str)): simulator will sleep for this amount of time between batches
        sub_id (str): source subscription (default = 'ztf_alert_data-reservoir')
        topic_id (str): sink topic (default = 'ztf_alert_data-{testid}')
        nack (bool): If True, the subscriber will "nack" the messages causing them to stay in the reservoir 
            and be delivered again at an arbitrary time in the future. If False, messages are acknowledged 
            and disappear from the reservoir.
    """
    
    pbeN, pbeU = publish_batch_every  # shorthand

    # get number of alerts to publish per batch
    alerts_per_batch, aRate_tuple = get_number_alerts_per_batch(alertRate, publish_batch_every)   # int, tuple

    # get number of batches to run
    Nbatches = convert_runTime_to_Nbatches(runTime, publish_batch_every, aRate_tuple[1])

    # tell the user about the rates
    print(f"\nReceived desired alertRate={aRate_tuple}, runTime={runTime}.")
    print(f"\nPublishing {Nbatches} batches, each with {alerts_per_batch} alerts, at a rate of 1 batch per {pbeN} {pbeU} (plus processing time).\n")

    # publish the stream
    do_publish_stream(testid, alerts_per_batch, Nbatches, publish_batch_every, sub_id, topic_id, nack)


def do_publish_stream(
    testid, alerts_per_batch, Nbatches, publish_batch_every, sub_id=None, topic_id=None, nack=False):

    # check units
    if publish_batch_every[1] != 'sec':
        raise ValueError("Units of publish_batch_every must = 'sec'.")

    # setup for subscription pulls and publishing
    subscriber, sub_path, request = setup_subscribe(alerts_per_batch, sub_id)
    publisher, topic_path = setup_publish(testid, alerts_per_batch, topic_id)
    print(f"\nReservoir (source subscription): {sub_path}")
    print(f"Publish topic (sink topic): {topic_path}\n")

    # make the user confirm
    user_confirm()
    print(f"\nPublishing...")

    b = 0
    while b < Nbatches:
        # get alerts from reservoir
        response = subscriber.pull(request=request)

        # publish alerts to topic, raise exception on failure
        publish_received_messages(publisher, topic_path, response)

        # ack or nack subscription messages
        ack_ids = [msg.ack_id for msg in response.received_messages]
        handle_acks(subscriber, sub_path, ack_ids, nack)

        # increment and sleep between batches 
        b = b+1
        time.sleep(publish_batch_every[0])

def user_confirm():
    cont = input('Continue? [Y/n]: ') or 'Y'
    if cont not in ['Y', 'y']:
        sys.exit('Exiting consumer simulator.')

def setup_subscribe(alerts_per_batch, sub_id=None):
    subscriber = pubsub.SubscriberClient()

    if sub_id is None: sub_id = 'ztf_alert_data-reservoir'
    
    sub_path = subscriber.subscription_path(PROJECT_ID, sub_id)
    
    request = {
            "subscription": sub_path,
            "max_messages": alerts_per_batch,
        }

    return (subscriber, sub_path, request)

def setup_publish(testid, alerts_per_batch, topic_id=None):
    # calls to publish are batched automatically
    # let's try to get all alerts into 1 publisher batch
    batch_settings = pubsub.types.BatchSettings(max_messages=alerts_per_batch)
    # some default batch settings to be aware of:
        # max_messages = 100
        # max_bytes = 1 MB
        # max_latency = 10 ms

    publisher = pubsub.PublisherClient(batch_settings)

    if topic_id is None: topic_id = f'ztf_alert_data-{testid}'
    topic_path = publisher.topic_path(PROJECT_ID, topic_id)

    return (publisher, topic_path)

def publish_received_messages(publisher, topic_path, sub_response):
    """ Iterate through messages and publish them, along with their attributes, to the Pub/Sub topic.
    """
    for msg in sub_response.received_messages:
        # print("Received message:", msg.message.data)
        attrs = msg.message.attributes  # pass msg attributes through

        future = publisher.publish(topic_path, msg.message.data, **attrs)  # non blocking
        
        future.add_done_callback(callback)  # check for errors in a separate thread

def handle_acks(subscriber, sub_path, ack_ids=[], nack=False):
    """ If nack is False, acknowledge messages, else nack them so they stay in the reservoir.
    """
    if not nack:
        subscriber.acknowledge(
            request={
                "subscription": sub_path,
                "ack_ids": ack_ids,
            }
        )
    else:
        subscriber.modify_ack_deadline(
            request={
                "subscription": sub_path,
                "ack_ids": ack_ids,
                "ack_deadline_seconds": 0,
            }
        )

def callback(future):
    # Publishing failures are automatically retried, except for errors that do not warrant retries.
    message_id = future.result() # raises an exception if publish ultimately failed
    # print(message_id)

def convert_runTime_to_Nbatches(runTime, publish_batch_every, aRate_unit):
    if aRate_unit == 'once':
        Nbatches = 1
    
    elif type(runTime) != tuple:
        msg = "runTime must be given as a tuple, unless the alertRate units are set to 'once'"
        raise ValueError(msg)

    else:
        pbeN, pbeU = publish_batch_every  # shorthands
        publish_runTime = convert_time_to_publish_unit(runTime, pbeU)  # int
        Nbatches = convert_publish_runTime_to_Nbatches(publish_runTime, pbeN)  # int

    return Nbatches

def convert_publish_runTime_to_Nbatches(publish_runTime, publish_batch_every_N):
    """
    Args:
        publish_runTime (int or float): runTime requested by user, in units used by the publisher
        publish_batch_every_N (int): publisher will use a rate of 1 batch per publish_batch_every_N. 
        Should be in the same units as publish_runTime.
    Returns:
        Nbatches (int): number of batches the publisher should complete, rounded to an int
    """
    Nbatches = publish_runTime * (1/publish_batch_every_N)
    return int(Nbatches)

def convert_time_to_publish_unit(runTime, publish_unit):
    """
    Args:
        runTime (int, str): (number, unit) to convert to publish_unit
        publish_unit (str): time units consumer will use for publish rate

    Returns:
        publish_runTime (int): runTime converted to publish_unit
    """

    rtN, rtU = runTime
    
    # convert the time to (N, 'sec')
    if publish_unit == 'sec':
        if rtU == 'sec':
            publish_runTime = rtN
        elif rtU == 'min':
            publish_runTime = rtN*60
        elif rtU == 'hr':
            publish_runTime = rtN*3600
        elif rtU == 'night':
            publish_runTime = rtN*10*3600

    else:
        msg = f"received publish_units='{publish_unit}', but only configured for publish_unit='sec'"
        raise ValueError(msg)

    return publish_runTime

def get_number_alerts_per_batch(alertRate, publish_batch_every):
    """ Find the number of alerts to publish per batch
    """

    aRate_tuple = convert_rate_to_tuple(alertRate)  #tuple

    # if user requested 1 batch, return their number
    if aRate_tuple[1]=='once':
        alerts_per_batch = aRate_tuple[0]

    # else convert to batch rate
    else:
        pbeN, pbeU = publish_batch_every
        avg_publish_rate = convert_rate_to_publish_unit(aRate_tuple, publish_unit=pbeU)  # float
        alerts_per_batch = get_number_alerts_per_batch_from_avg(avg_publish_rate, pbeN)  # int, per batch

    return (alerts_per_batch, aRate_tuple)

def get_number_alerts_per_batch_from_avg(avg_publish_rate, publish_interval):
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

def convert_rate_to_tuple(alertRate):

    # make sure we have a type that has been configured
    if type(alertRate)!=str:
        if type(alertRate) != tuple:
            msg = 'alertRate must be a tuple or a string'
            raise ValueError(msg)

        else:
            # type == tuple, so just return it
            aRate = alertRate

    # convert strings to tuples
    elif alertRate=='ztf-active-avg':
        aRate = (250000, 'perNight')
    elif alertRate == 'ztf-max':
        aRate = (5000, 'perMin')
    else:
        msg = f"'ztf-active-avg' and 'ztf-max' are the only strings currently configured for the alertRate"
        raise ValueError(msg)

    return aRate
