#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``pubsub`` contains functions that facilitate listening to and decoding
Pitt-Google Broker's Pub/Sub streams.
"""

from google.cloud import pubsub

# subscriber, sub_path, request = setup_subscribe(alerts_per_batch, sub_id)
def setup_subscribe(alerts_per_batch, sub_id=None):
    subscriber = pubsub.SubscriberClient()

    if sub_id is None: sub_id = 'ztf_alert_data-reservoir'

    sub_path = subscriber.subscription_path(PROJECT_ID, sub_id)

    request = {
            "subscription": sub_path,
            "max_messages": alerts_per_batch,
        }

    return (subscriber, sub_path, request)

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

# response = subscriber.pull(request=request)
# for msg in response.received_messages:
#     # print("Received message:", msg.message.data)
#     attrs = msg.message.attributes  # pass msg attributes through
#
#     future = publisher.publish(topic_path, msg.message.data, **attrs)  # non
#
# ack_ids = [msg.ack_id for msg in response.received_messages]
# handle_acks(subscriber, sub_path, ack_ids, nack)


#-- Create or delete subscriptions

    # for sub_name in subscriptions:
    #     sub_path = subscriber.subscription_path(PROJECT_ID, sub_name)
    #     if teardown:
    #         # Delete subscription
    #         try:
    #             subscriber.delete_subscription(request={"subscription": sub_path})
    #         except NotFound:
    #             pass
    #         else:
    #             print(f'Deleted subscription {sub_name}')
    #     else:
    #         try:
    #             subscriber.get_subscription(subscription=sub_path)
    #         except NotFound:
    #             # Create subscription
    #             subscriber.create_subscription(name=sub_path, topic=topic_path)
    #             print(f'Created subscription {sub_name}')
