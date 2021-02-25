"""Publish and retrieve messages via Pub/Sub."""

import logging
import os
from google.cloud import pubsub_v1

log = logging.getLogger(__name__)

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')


def publish_pubsub(topic_name, message):
    """Publish encoded messages to a Pub/Sub topic

    Args:
        topic_name  (str): The Pub/Sub topic name for publishing alerts
        message     (bytes): The message to be published, already encoded
    """

    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(project_id, topic_name)

    # topic = publisher.get_topic(topic_path)
    log.info(f'Connected to PubSub: {topic_path}')

    future = publisher.publish(topic_path, data=message)

    return future.result()


def subscribe_alerts(subscription_name, max_alerts=1):
    """Download, decode, and return messages from a Pub/Sub topic

    Args:
        subscription_name   (str): The Pub/Sub subcription name linked to a Pub/Sub topic
        max_alerts          (int): The maximum number of alerts to download

    Returns:
        A list of downloaded and decoded messages
    """

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    response = subscriber.pull(subscription_path, max_messages=max_alerts)

    message_list, ack_ids = [], []

    for received_message in response.received_messages:
        encoded = received_message.message.data
        message = encoded.decode('UTF-8')
        message_list.append(message)
        ack_ids.append(received_message.ack_id)

    subscriber.acknowledge(subscription_path, ack_ids)

    return (message_list)
