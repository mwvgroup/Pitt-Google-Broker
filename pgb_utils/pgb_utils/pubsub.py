#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``pubsub`` module facilitates interacting with Pitt-Google Pub/Sub streams.

publishing, pulling subscriptions, and decoding alert streams.
"""

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.subscriber.futures import StreamingPullFuture
from google.cloud.pubsub_v1.types import PubsubMessage, ReceivedMessage
import os
from typing import Callable, List, Optional, Union


pgb_project_id = "ardent-cycling-243415"


# --- Pull messages --- #
def pull(
    subscription_name: str,
    max_messages: int = 1,
    project_id: Optional[str] = None,
    msg_only: bool = True,
) -> Union[List[bytes], List[ReceivedMessage]]:
    """Pull and acknowledge a fixed number of messages from a Pub/Sub topic.

    Wrapper for the synchronous
    `google.cloud.pubsub_v1.SubscriberClient().pull()`.
    See also: https://cloud.google.com/pubsub/docs/pull#synchronous_pull

    Args:
        subscription_name: Name of the Pub/Sub subcription to pull from.

        max_messages: The maximum number of messages to pull.

        project_id: GCP project ID for the project containing the subscription.
                    If None, the environment variable GOOGLE_CLOUD_PROJECT will be used.

        msg_only: Whether to return the message contents only or the full packet.

    Returns:
        A list of messages
    """
    if project_id is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    # setup for pull
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    request = {
        "subscription": subscription_path,
        "max_messages": max_messages,
    }

    # wrap in 'with' block to automatically call close() when done
    with subscriber:

        # pull
        response = subscriber.pull(**request)

        # unpack the messages
        message_list, ack_ids = [], []
        for received_message in response.received_messages:
            if msg_only:
                message_list.append(received_message.message.data)  # bytes
            else:
                message_list.append(received_message)
            ack_ids.append(received_message.ack_id)

        # acknowledge the messages so they will not be sent again
        ack_request = {
            "subscription": subscription_path,
            "ack_ids": ack_ids,
        }
        subscriber.acknowledge(**ack_request)

    return message_list


def streamingPull(
    subscription_name: str,
    callback: Callable[[PubsubMessage], None],
    project_id: str = None,
    timeout: int = 10,
    block: bool = True
) -> Union[None, StreamingPullFuture]:
    """Pull and process Pub/Sub messages continuously in a background thread.

    Wrapper for the asynchronous
    `google.cloud.pubsub_v1.SubscriberClient().subscribe()`.
    See also: https://cloud.google.com/pubsub/docs/pull#asynchronous-pull

    Args:
        subscription_name: The Pub/Sub subcription to pull from.

        callback: The callback function containing the message processing and
                  acknowledgement logic.

        project_id: GCP project ID for the project containing the subscription.
                    If None, the environment variable GOOGLE_CLOUD_PROJECT will be used.

        timeout: The amount of time, in seconds, the subscriber client should wait for
                 a new message before closing the connection.

        block: Whether to block while streaming messages or return the
               StreamingPullFuture object for the user to manage separately.

    Returns:
        If `block` is False, immediately returns the StreamingPullFuture object that
        manages the background thread.
        Call its `cancel()` method to stop streaming messages.
        If `block` is True, returns None once the streaming encounters an error
        or timeout.
    """
    if project_id is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    # start receiving and processing messages in a background thread
    streaming_pull_future = subscriber.subscribe(subscription_path, callback)

    if block:
        # block until there are no messages for the timeout duration
        # or an error is encountered
        with subscriber:
            try:
                streaming_pull_future.result(timeout=timeout)
            except TimeoutError:
                streaming_pull_future.cancel()  # Trigger the shutdown.
                streaming_pull_future.result()  # Block until the shutdown is complete.

    else:
        return streaming_pull_future


# --- Publish --- #
def publish(
    topic_name: str, message: bytes, project_id: Optional[str] = None, attrs: dict = {}
) -> str:
    """Publish messages to a Pub/Sub topic.

    Wrapper for `google.cloud.pubsub_v1.PublisherClient().publish()`.
    See also: https://cloud.google.com/pubsub/docs/publisher#publishing_messages.

    Args:
        topic_name: The Pub/Sub topic name for publishing alerts.

        message: The message to be published.

        project_id: GCP project ID for the project containing the topic.
                    If None, the environment variable GOOGLE_CLOUD_PROJECT will be used.

        attrs: Message attributes to be published.

    Returns:
        published message ID
    """
    if project_id is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(project_id, topic_name)

    future = publisher.publish(topic_path, data=message, **attrs)

    return future.result()


# --- Subscribe to a PGB stream from an external account --- #
def create_subscription(
    topic_name: str,
    project_id: Optional[str] = None,
    subscription_name: Optional[str] = None,
):
    """Create a subscription to a Pitt-Google Pub/Sub topic.

    Wrapper for `google.cloud.pubsub_v1.SubscriberClient().create_subscription()`.
    See also: https://cloud.google.com/pubsub/docs/admin#manage_subs

    Args:
        topic_name: Name of a Pitt-Google Broker Pub/Sub topic to subscribe to.
        project_id: User's GCP project ID. If None, the environment variable
                    GOOGLE_CLOUD_PROJECT will be used. The subscription will be
                    created in this account.
        subscription_name: Name for the user's Pub/Sub subscription. If None,
                           `topic_name` will be used.
    """
    if project_id is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if subscription_name is None:
        subscription_name = topic_name

    subscriber = pubsub_v1.SubscriberClient()
    publisher = pubsub_v1.PublisherClient()

    sub_path = subscriber.subscription_path(project_id, subscription_name)
    topic_path = publisher.topic_path(pgb_project_id, topic_name)

    subscription = subscriber.create_subscription(sub_path, topic_path)

    print(f"Created subscription {subscription.name}")
    print(f"attached to topic {subscription.topic}")

    return subscription


# --- Delete a subscription --- #
def delete_subscription(subscription_name: str, project_id: Optional[str] = None) -> None:
    """Delete a Pub/Sub subscription.

    Wrapper for `google.cloud.pubsub_v1.SubscriberClient().delete_subscription()`.
    See also: https://cloud.google.com/pubsub/docs/admin#delete_subscription

    Args:
        subscription_name: Name for the user's Pub/Sub subscription. If None,
                           `topic_name` will be used.
        project_id: User's GCP project ID. If None, the environment variable
                    GOOGLE_CLOUD_PROJECT will be used. The subscription will be
                    created in this account.
    """
    if project_id is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    request = {"subscription": subscription_path}

    with subscriber:
        subscriber.delete_subscription(**request)

    print(f"Subscription deleted: {subscription_path}.")
