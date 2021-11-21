#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``pubsub`` contains functions that facilitate listening to and decoding
Pitt-Google Broker's Pub/Sub streams.
"""
from typing import Callable, List, Optional, Union
from google.api_core.exceptions import NotFound
from google.cloud import pubsub
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import ReceivedMessage


pgb_project_id = 'ardent-cycling-243415'


def pull_pubsub(
    subscription_name: str,
    max_messages: int = 1,
    project_id: Optional[str] = None,
    msg_only: bool = True,
    callback: Optional[Callable[[Union[ReceivedMessage, bytes]], bool]] = None,
    return_count: bool = False,
) -> Union[List[bytes], List[ReceivedMessage]]:
    """Pull and acknowledge a fixed number of messages from a Pub/Sub topic.

    Wrapper for the synchronous
    `google.cloud.pubsub_v1.SubscriberClient().pull()`.
    See also: https://cloud.google.com/pubsub/docs/pull#synchronous_pull

    Args:
        subscription_name: Name of the Pub/Sub subcription to pull from.

        max_messages: The maximum number of messages to pull.

        project_id: GCP project ID for the project containing the subscription.
                    If None, the module's `pgb_project_id` will be used.

        msg_only: Whether to work with and return the message contents only
                  or the full packet.
                  If `return_count` is True, it supersedes the returned object.

        callback: Function used to process each message.
                  Its input type is determined by the value of `msg_only`.
                  It should return True if the message should be acknowledged,
                  else False.

        return_count: Whether to return the messages or just the total number of
                      acknowledged messages.

    Returns:
        A list of messages
    """
    subscriber = pubsub_v1.SubscriberClient()

    if project_id is None:
        project_id = pgb_project_id

    # setup for pull
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    request = {
        "subscription": subscription_path,
        "max_messages": max_messages,
    }

    # wrap in 'with' block to automatically call close() when done
    with subscriber:

        # pull
        response = subscriber.pull(request)

        # unpack the messages
        message_list, ack_ids = [], []
        for received_message in response.received_messages:

            if msg_only:
                # extract the message bytes and append
                msg_bytes = received_message.message.data
                message_list.append(msg_bytes)
                # perform callback, if requested
                if callback is not None:
                    success = callback(msg_bytes)

            else:
                # append the full message
                message_list.append(received_message)
                # perform callback, if requested
                if callback is not None:
                    success = callback(received_message)

            # collect ack_id, if appropriate
            if (callback is None) or (success):
                ack_ids.append(received_message.ack_id)

        # acknowledge the messages so they will not be sent again
        if len(ack_ids) > 0:
            ack_request = {
                "subscription": subscription_path,
                "ack_ids": ack_ids,
            }
            subscriber.acknowledge(ack_request)

    if not return_count:
        return message_list
    else:
        return len(message_list)


def create_subscription(topic_name: str, subscription_name: Optional[str] = None, project_id: Optional[str] = None):
    """Try to create the subscription."""
    subscriber = pubsub_v1.SubscriberClient()

    if project_id is None:
        project_id = pgb_project_id

    if subscription_name is None:
        subscription_name = topic_name

    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    topic_path = f"projects/{project_id}/topics/{subscription_name}"

    try:
        subscriber.create_subscription(
            name=subscription_path, topic=topic_path
        )
    except NotFound:
        # suitable topic does not exist in the Pitt-Google project
        raise ValueError(
            (
                f"A subscription named {subscription_name} does not exist"
                "in the Google Cloud Platform project "
                f"{project_id}, "
                "and one cannot be automatically create because Pitt-Google "
                "does not publish a public topic with the same name."
            )
        )
    else:
        print(f"Created subscription: {subscription_path}")


def delete_subscription(subscription_name: str, project_id: Optional[str] = None):
    """Delete the subscription.

    This is provided for the user's convenience, but it is not necessary and is not
    automatically called.

        - Storage of unacknowledged Pub/Sub messages does not result in fees.

        - Unused subscriptions automatically expire; default is 31 days.
    """
    subscriber = pubsub_v1.SubscriberClient()

    if project_id is None:
        project_id = pgb_project_id

    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    try:
        subscriber.delete_subscription(subscription=subscription_path)
    except NotFound:
        pass
    else:
        print(f'Deleted subscription: {subscription_path}')


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
