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

timeout = 50.0
testid='test'
topic_name = 'troy_test_topic'

max_alerts = 1
Nmax=400
rate = Nmax # alerts/min
waitsec = 1/(rate/60)

subscription_id = 'ztf_alert_data_subtest'
subscription_path = subscriber.subscription_path(project_id, subscription_id)


# msglist = psms.subscribe_alerts(subscription_id, max_alerts=1, decode=True)
# does not work

subscriber = pubsub_v1.SubscriberClient()

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

# Wrap subscriber in a 'with' block to automatically call close() when done.
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
