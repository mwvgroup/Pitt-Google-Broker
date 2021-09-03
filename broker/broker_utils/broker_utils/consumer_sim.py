#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
""" Simulate the consumer by publishing alerts to a Pub/Sub topic.
"""

from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1
import os
import sys
import time
from typing import Optional, Tuple, Union
from warnings import warn

PROJECT_ID = 'ardent-cycling-243415'


def publish_stream(
    alert_rate: Union[Tuple[int,str],str],
    instance: Optional[Tuple[str,str]] = None,
    runtime: Optional[Tuple[int,str]] = None,
    publish_batch_every: Tuple[int,str] = (5,'sec'),
    sub_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    nack: bool = False,
    auto_confirm: bool = False
    ):
    """Pulls messages from from a Pub/Sub subscription determined by either
    `instance` or `sub_id`, and publishes them to a topic determined by either
    `instance` or `topic_id`. Specific options are described in the docs.

    Args:
        alert_rate:  Desired rate at which alerts will be published.

        instance:   (survey, testid). Keywords of the broker instance. Used to
                    determine the subscription and topic. If `None`, `sub_id`
                    and `topic_id` must be valid names. If both `instance` and
                    `sub_id`/`topic_id` are passed, `sub_id`/`topic_id` will
                    prevail.

        runtime:    Desired length of time simulator runs for.

        publish_batch_every:    Simulator will sleep for this amount of time
                                between batches

        sub_id:     Name of the Pub/Sub subscription from which to pull alerts.
                    If `None`, `instance` must contain valid keywords, and then
                    the production instance reservoir
                    '{survey}-alerts-reservoir' will be used.

        topic_id:   Name of the Pub/Sub topic to which alerts will be published.
                    If `None`, `instance` must contain valid keywords, and then
                    the topic '{survey}-alerts-{testid}' will be used.

        nack:       Whether to "nack" (not acknowledge) the messages. If `True`,
                    messages are published to the topic, but they are not
                    dropped from the subscription and so will be delivered again
                    at an arbitrary time in the future.

        auto_confirm:   Whether to automatically answer "Y" to the confirmation prompt.
    """

    pbeN, pbeU = publish_batch_every  # shorthand

    # get number of alerts to publish per batch
    alerts_per_batch, aRate_tuple = _get_number_alerts_per_batch(alert_rate, publish_batch_every)   # int, tuple

    # get number of batches to run
    Nbatches = _convert_runtime_to_Nbatches(runtime, publish_batch_every, aRate_tuple[1])

    # tell the user about the rates
    print(f"\nReceived desired alert_rate={aRate_tuple}, runtime={runtime}.")
    print(f"\nPublishing:\n\t{Nbatches} batches\n\teach with {alerts_per_batch} alerts\n\tat a rate of 1 batch per {pbeN} {pbeU} (plus processing time)\n\tfor a total of {Nbatches*alerts_per_batch} alerts")

    # publish the stream
    _do_publish_stream(instance, alerts_per_batch, Nbatches, publish_batch_every, sub_id, topic_id, nack, auto_confirm)

def _do_publish_stream(
    instance, alerts_per_batch, Nbatches, publish_batch_every, sub_id=None, topic_id=None, nack=False, auto_confirm=False):

    # check units
    if publish_batch_every[1] != 'sec':
        raise ValueError("Units of publish_batch_every must = 'sec'.")

    # setup for subscription pulls and publishing
    subscriber, sub_path, request = _setup_subscribe(alerts_per_batch, instance, sub_id)
    publisher, topic_path = _setup_publish(alerts_per_batch, instance, topic_id)
    print(f"\nThis will\n\tPull from subscription: {sub_path}")
    print(f"and\n\tPublish to topic: {topic_path}\n")

    # make the user confirm
    _user_confirm(auto_confirm)
    print(f"\nPublishing...")

    b = 0
    while b < Nbatches:
        # get alerts from reservoir
        # response = subscriber.pull(request=request)  # for pubsub2+
        response = subscriber.pull(**request)

        # publish alerts to topic, raise exception on failure
        _publish_received_messages(publisher, topic_path, response)

        # ack or nack subscription messages
        ack_ids = [msg.ack_id for msg in response.received_messages]
        _handle_acks(subscriber, sub_path, ack_ids, nack)

        # increment and sleep between batches
        b = b+1
        time.sleep(publish_batch_every[0])

def _user_confirm(auto_confirm=False):
    if not auto_confirm:
        cont = input('Continue? [Y/n]: ') or 'Y'
        if cont not in ['Y', 'y']:
            sys.exit('Exiting consumer simulator.')

def _setup_subscribe(alerts_per_batch, instance=None, sub_id=None):
    if (instance is None) and (sub_id is None):
        raise ValueError('Must provide either `instance` or `sub_id`.')

    if sub_id is None:
        # use the reservoir of the production instance for this survey
        survey = instance[0]
        sub_id = f'{survey}-alerts-reservoir'

    subscriber = pubsub_v1.SubscriberClient()
    sub_path = subscriber.subscription_path(PROJECT_ID, sub_id)
    request = {
            "subscription": sub_path,
            "max_messages": alerts_per_batch,
        }

    return (subscriber, sub_path, request)

def _setup_publish(alerts_per_batch, instance=None, topic_id=None):
    if (instance is None) and (topic_id is None):
        raise ValueError('Must provide either `instance` or `topic_id`.')

    if topic_id is None:
        survey, testid = instance
        topic_id = f'{survey}-alerts-{testid}'

    # calls to publish are batched automatically
    # let's try to get all alerts into 1 publisher batch
    batch_settings = pubsub_v1.types.BatchSettings(max_messages=alerts_per_batch)
    # some default batch settings to be aware of:
        # max_messages = 100
        # max_bytes = 1 MB
        # max_latency = 10 ms
    publisher = pubsub_v1.PublisherClient(batch_settings)
    topic_path = publisher.topic_path(PROJECT_ID, topic_id)

    return (publisher, topic_path)

def _publish_received_messages(publisher, topic_path, sub_response):
    """ Iterate through messages and publish them, along with their attributes, to the Pub/Sub topic.
    """
    for msg in sub_response.received_messages:
        # print("Received message:", msg.message.data)
        attrs = msg.message.attributes  # pass msg attributes through

        future = publisher.publish(topic_path, msg.message.data, **attrs)  # non blocking

        future.add_done_callback(_callback)  # check for errors in a separate thread

def _handle_acks(subscriber, sub_path, ack_ids=[], nack=False):
    """ If nack is False, acknowledge messages, else nack them so they stay in the reservoir.
    """
    if not nack:
        request={
            "subscription": sub_path,
            "ack_ids": ack_ids,
        }
        subscriber.acknowledge(**request)
    else:
        request={
            "subscription": sub_path,
            "ack_ids": ack_ids,
            "ack_deadline_seconds": 0,
        }
        subscriber.modify_ack_deadline(**request)

def _callback(future):
    # Publishing failures are automatically retried, except for errors that do not warrant retries.
    message_id = future.result() # raises an exception if publish ultimately failed
    # print(message_id)

def _convert_runtime_to_Nbatches(runtime, publish_batch_every, aRate_unit):
    if aRate_unit == 'once':
        Nbatches = 1

    elif type(runtime) != tuple:
        msg = "runtime must be given as a tuple, unless the alert_rate units are set to 'once'"
        raise ValueError(msg)

    else:
        pbeN, pbeU = publish_batch_every  # shorthands
        publish_runtime = _convert_time_to_publish_unit(runtime, pbeU)  # int
        Nbatches = _convert_publish_runtime_to_Nbatches(publish_runtime, pbeN)  # int

    return Nbatches

def _convert_publish_runtime_to_Nbatches(publish_runtime, publish_batch_every_N):
    """
    Args:
        publish_runtime (int or float): runtime requested by user, in units used by the publisher
        publish_batch_every_N (int): publisher will use a rate of 1 batch per publish_batch_every_N.
        Should be in the same units as publish_runtime.
    Returns:
        Nbatches (int): number of batches the publisher should complete, rounded to an int
    """
    Nbatches = publish_runtime * (1/publish_batch_every_N)
    return int(Nbatches)

def _convert_time_to_publish_unit(runtime, publish_unit):
    """
    Args:
        runtime (int, str): (number, unit) to convert to publish_unit
        publish_unit (str): time units consumer will use for publish rate

    Returns:
        publish_runtime (int): runtime converted to publish_unit
    """

    rtN, rtU = runtime

    # convert the time to (N, 'sec')
    if publish_unit == 'sec':
        if rtU == 'sec':
            publish_runtime = rtN
        elif rtU == 'min':
            publish_runtime = rtN*60
        elif rtU == 'hr':
            publish_runtime = rtN*3600
        elif rtU == 'night':
            publish_runtime = rtN*10*3600

    else:
        msg = f"received publish_units='{publish_unit}', but only configured for publish_unit='sec'"
        raise ValueError(msg)

    return publish_runtime

def _get_number_alerts_per_batch(alert_rate, publish_batch_every):
    """ Find the number of alerts to publish per batch
    """

    aRate_tuple = _convert_rate_to_tuple(alert_rate)  #tuple

    # if user requested 1 batch, return their number
    if aRate_tuple[1]=='once':
        alerts_per_batch = aRate_tuple[0]

    # else convert to batch rate
    else:
        pbeN, pbeU = publish_batch_every
        avg_publish_rate = _convert_rate_to_publish_unit(aRate_tuple, publish_unit=pbeU)  # float
        alerts_per_batch = _get_number_alerts_per_batch_from_avg(avg_publish_rate, pbeN)  # int, per batch

    return (alerts_per_batch, aRate_tuple)

def _get_number_alerts_per_batch_from_avg(avg_publish_rate, publish_interval):
    return int(avg_publish_rate*publish_interval)

def _convert_rate_to_publish_unit(alert_rate, publish_unit='sec'):
    """
    Args:
        alert_rate (int, str): (number, unit) to convert to publish_unit
        publish_unit (str): time units consumer will use for publish rate

    Returns:
        alerts_per_unit (float): alert_rate in units per publish_unit
    """

    arN, arU = alert_rate

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

def _convert_rate_to_tuple(alert_rate):

    if type(alert_rate) == tuple:
        # type == tuple, so just return it
        aRate = alert_rate

    elif type(alert_rate) == str:
        aRate = _convert_rate_string_to_tuple(alert_rate)
        # returns tuple or raises ValueError

    else:
        msg = 'alert_rate must be a tuple or a string'
        raise ValueError(msg)

    return aRate

def _convert_rate_string_to_tuple(alert_rate):
    # convert strings to tuples

    if alert_rate=='ztf-active-avg':
        aRate = (300000, 'perNight')

    elif alert_rate == 'ztf-live-max':
        aRate = (200, 'perSec')

    else:
        msg = f"'ztf-active-avg' and 'ztf-live-max' are the only strings currently configured for the alert_rate"
        raise ValueError(msg)

    return aRate
