"""Publish and retrieve messages via Pub/Sub."""

import pickle

from google.cloud import pubsub_v1


def publish_alerts(project_id, topic_name, alerts):
    """Publish encoded, simplified messages to a Pub/Sub topic
    
    Args:
        project_id  (str): The GCP project ID number
        topic_name  (str): The Pub/Sub topic name for publishing alerts
        alerts     (list): The list of ZTF alerts to be published
    """

    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(project_id, topic_name)

    for alert in alerts:
        alert.pop("cutoutScience")
        alert.pop("cutoutTemplate")
        alert.pop("cutoutDifference")

        pickled = pickle.dumps(alert)

        publisher.publish(topic_path, data=pickled)


def subscribe_alerts(project_id, subscription_name, max_alerts=1):
    """Download, decode, and return messages from a Pub/Sub topic
    
    Args:
        project_id          (int): The GCP project ID number
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
        message = pickle.loads(encoded)
        message_list.append(message)
        ack_ids.append(received_message.ack_id)

    subscriber.acknowledge(subscription_path, ack_ids)

    return (message_list)
