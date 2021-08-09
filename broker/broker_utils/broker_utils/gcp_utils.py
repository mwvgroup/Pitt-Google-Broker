#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``gcp_utils`` module contains common functions used to interact with
GCP resources.
"""

from google.cloud import bigquery, pubsub_v1, storage
from google.cloud.pubsub_v1.subscriber.futures import StreamingPullFuture
from google.cloud.pubsub_v1.types import PubsubMessage, ReceivedMessage
from typing import Callable, List, Optional, Union

pgb_project_id = 'ardent-cycling-243415'


# --- Pub/Sub --- #
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
        project_id = pgb_project_id

    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(project_id, topic_name)

    future = publisher.publish(topic_path, data=message, **attrs)

    return future.result()


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
        project_id = pgb_project_id

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
        project_id = pgb_project_id

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    # start receiving and processing messages in a background thread
    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback
    )

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


# --- BigQuery --- #
def bq_insert_rows(table_id: str, rows: List[dict]):
    """
    Args:
        table_id:   Identifier for the BigQuery table in the form
                    {dataset}.{table}. For example, 'ztf_alerts.alerts'.
        rows:       Data to load in to the table. Keys must include all required
                    fields in the schema. Keys which do not correspond to a
                    field in the schema are ignored.
    """
    bq_client = bigquery.Client(project=pgb_project_id)
    table = bq_client.get_table(table_id)
    errors = bq_client.insert_rows(table, rows)


# --- Cloud Storage --- #
def cs_download_file(localdir: str, bucket_id: str, filename: Optional[str] = None):
    """
    Args:
        localdir:   Path to local directory where file(s) will be downloaded to.
        bucket_id:  Name of the GCS bucket, not including the project ID.
                    For example, pass 'ztf-alert_avros' for the bucket
                    'ardent-cycling-243415-ztf-alert_avros'.
        filename:   Name or prefix of the file(s) in the bucket to download.
    """
    # connect to the bucket and get an iterator that finds blobs in the bucket
    storage_client = storage.Client(pgb_project_id)
    bucket_name = f'{pgb_project_id}-{bucket_id}'
    print(f'Connecting to bucket {bucket_name}')
    bucket = storage_client.get_bucket(bucket_name)
    blobs = storage_client.list_blobs(bucket, prefix=filename)  # iterator

    # download the files
    for blob in blobs:
        local_path = f'{localdir}/{blob.name}'
        blob.download_to_filename(local_path)
        print(f'Downloaded {local_path}')


def cs_upload_file(local_file: str, bucket_id: str, bucket_filename: Optional[str] = None):
    """
    Args:
        local_file: Path of the file to upload.
        bucket_id:  Name of the GCS bucket, not including the project ID.
                    For example, pass 'ztf-alert_avros' for the bucket
                    'ardent-cycling-243415-ztf-alert_avros'.
        bucket_filename:    String to name the file in the bucket. If None,
                            bucket_filename = local_filename.
    """
    if bucket_filename is None:
        bucket_filename = local_file.split('/')[-1]

    # connect to the bucket
    storage_client = storage.Client(pgb_project_id)
    bucket_name = f'{pgb_project_id}-{bucket_id}'
    print(f'Connecting to bucket {bucket_name}')
    bucket = storage_client.get_bucket(bucket_name)

    # upload
    blob = bucket.blob(bucket_filename)
    blob.upload_from_filename(local_file)
    print(f'Uploaded {local_file} as {bucket_filename}')
