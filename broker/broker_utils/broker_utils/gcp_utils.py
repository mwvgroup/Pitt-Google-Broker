#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``gcp_utils`` module contains common functions used to interact with
GCP resources.
"""

from google.cloud import bigquery, pubsub_v1, storage
from google.cloud.logging_v2.logger import Logger
from google.cloud.pubsub_v1.subscriber.futures import StreamingPullFuture
from google.cloud.pubsub_v1.types import PubsubMessage, ReceivedMessage
import json
import pandas as pd
from typing import Callable, List, Optional, Union

pgb_project_id = 'ardent-cycling-243415'


# --- Pub/Sub --- #
def publish_pubsub(
    topic_name: str,
    message: Union[bytes, dict],
    project_id: Optional[str] = None,
    attrs: dict = {},
    publisher: Optional[pubsub_v1.PublisherClient] = None
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

        publisher: An instantiated PublisherClient.
                   Use this kwarg if you are calling this function repeatedly.
                   The publisher will automatically batch the messages over a
                   small time window (currently 0.05 seconds) to avoid making
                   too many separate requests to the service.
                   This helps increase throughput. See
                   https://googleapis.dev/python/pubsub/1.7.0/publisher/index.html#batching

    Returns:
        published message ID
    """
    if project_id is None:
        project_id = pgb_project_id

    if publisher is None:
        publisher = pubsub_v1.PublisherClient()

    if type(message) == dict:
        message = json.dumps(message).encode('utf-8')
    try:
        assert type(message) == bytes
    except AssertionError:
        raise ValueError('`message` must be bytes or a dict.')

    topic_path = publisher.topic_path(project_id, topic_name)

    future = publisher.publish(topic_path, data=message, **attrs)

    return future.result()


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
                  It's input type is determined by the value of `msg_only`.
                  It should return True if the message should be acknowledged,
                  else False.

        return_count: Whether to return the messages or just the total number of
                      acknowledged messages.

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
            subscriber.acknowledge(**ack_request)

    if not return_count:
        return message_list
    else:
        return len(message_list)


def streamingPull_pubsub(
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
def insert_rows_bigquery(table_id: str, rows: List[dict]):
    """Insert rows into a table using the streaming API.

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
    return errors


def load_dataframe_bigquery(
    table_id: str,
    df: pd.DataFrame,
    use_table_schema: bool = True,
    logger: Optional[Logger] = None,
):
    """Load a dataframe to a table.

    Args:
        table_id: Identifier for the BigQuery table in the form
            {dataset}.{table}. For example, 'ztf_alerts.alerts'.
        df: Data to load in to the table. If the  dataframe schema does not match the
            BigQuery table schema, must pass a valid `schema`.
        use_table_schema: Conform the dataframe to the table schema by converting
                          dtypes and dropping extra columns.
        logger: If not None, messages will be sent to the logger. Else, print them.
    """
    # setup
    bq_client = bigquery.Client(project=pgb_project_id)
    table = bq_client.get_table(table_id)

    if use_table_schema:
        # set a job_config; bigquery will try to convert df.dtypes to match table schema
        job_config = bigquery.LoadJobConfig(schema=table.schema)

        # make sure the df has the correct columns
        bq_col_names = [s.name for s in table.schema]
        # pad missing columns
        missing = [c for c in bq_col_names if c not in df.columns]
        for col in missing:
            df[col] = None
        # drop extra columns
        dropped = list(set(df.columns) - set(bq_col_names))  # grab so we can report
        df = df[bq_col_names]
        # tell the user what happened
        if len(dropped) > 0:
            msg = f'Dropping columns not in the table schema: {dropped}'
            if logger is not None:
                logger.log_text(msg, severity='INFO')
            else:
                print(msg)

    else:
        job_config = None

    # load the data
    job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Wait for the job to complete.

    # report the results
    msg = (
        f"Loaded {job.output_rows} rows to BigQuery table {table_id}.\n"
        f"The following errors were generated: {job.errors}"
    )
    if logger is not None:
        severity = 'DEBUG' if job.errors is not None else 'INFO'
        logger.log_text(msg, severity=severity)
    else:
        print(msg)



def query_bigquery(query: str, project_id: Optional[str] = None):
    """Query BigQuery.

    Example query:
        ``
        query = (
            f'SELECT * '
            f'FROM `{project_id}.{dataset}.{table}` '
            f'WHERE objectId={objectId} '
        )
        ``

    Example of working with the query_job:
        ``
        for r, row in enumerate(query_job):
            # row values can be accessed by field name or index
            print(f"objectId={row[0]}, candid={row['candid']}")
        ``
    """
    if project_id is None:
        project_id = pgb_project_id

    bq_client = bigquery.Client(project=project_id)
    query_job = bq_client.query(query)

    return query_job


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
