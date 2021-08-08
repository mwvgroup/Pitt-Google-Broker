#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The `pubsub` module facilitates access to Pitt-Google Pub/Sub streams."""

from astropy.table import Table
from fastavro import reader
from google.cloud import pubsub_v1
# note: the 'v1' refers to the underlying API, not the google.cloud.pubsub version
from google.cloud.pubsub_v1.subscriber.futures import StreamingPullFuture
from google.cloud.pubsub_v1.types import PubsubMessage, ReceivedMessage, Subscription
from io import BytesIO
import json
import os
import pandas as pd
from typing import Callable, List, Optional, Tuple, Union


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
    `google.cloud.pubsub_v1.SubscriberClient().pull()`
    documented at
    https://googleapis.dev/python/pubsub/latest/subscriber/api/client.html.

    See also: https://cloud.google.com/pubsub/docs/pull

    Args:
        subscription_name: Name of the Pub/Sub subcription to pull from.

        max_messages: The maximum number of messages to pull.

        project_id: GCP project ID for the project containing the subscription.
                    If None, the environment variable GOOGLE_CLOUD_PROJECT will be used.

        msg_only: Whether to return the message contents only or the full packet.

    Returns:
        A list of messages. If `msg_only` is True, the messages are bytes containing
        the message data only. Otherwise the messages are the full message packets.
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
        response = subscriber.pull(request=request)

        # unpack the messages
        message_list, ack_ids = [], []
        for received_message in response.received_messages:
            if msg_only:
                message_list.append(received_message.message.data)  # bytes
            else:
                message_list.append(received_message)
                # https://cloud.google.com/pubsub/docs/reference/rpc/google.pubsub.v1#google.pubsub.v1.ReceivedMessage

            ack_ids.append(received_message.ack_id)

        # acknowledge the messages so they will not be sent again
        ack_request = {
            "subscription": subscription_path,
            "ack_ids": ack_ids,
        }
        subscriber.acknowledge(request=ack_request)

    return message_list


def streamingPull(
    subscription_name: str,
    callback: Callable[[PubsubMessage], None],
    project_id: str = None,
    block: bool = True
) -> Union[None, StreamingPullFuture]:
    """Pull and process Pub/Sub messages continuously in streaming mode.

    Wrapper for the asynchronous
    `google.cloud.pubsub_v1.SubscriberClient().subscribe()`
    documented at
    https://googleapis.dev/python/pubsub/latest/subscriber/api/client.html.

    See also: https://cloud.google.com/pubsub/docs/pull

    Args:
        subscription_name: The Pub/Sub subcription to pull from.

        callback: The callback function containing the message processing and
                  acknowledgement logic.

        project_id: GCP project ID for the project containing the subscription.
                    If None, the environment variable GOOGLE_CLOUD_PROJECT will be used.

        block: Whether to block while streaming messages or return the
               StreamingPullFuture object for the user to manage separately.

    Returns:
        If `block` is False, immediately returns the `StreamingPullFuture` object that
        manages the background thread that is pulling and processing messages.
        Call its `cancel()` method to stop streaming messages.

        If `block` is True, the user's thread is blocked until the streaming encounters
        an error.
        Use Control+C to stop streaming.
    """
    if project_id is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    # start receiving and processing messages in a background thread
    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback, await_callbacks_on_shutdown=True
    )

    if block:
        # block until there are no messages for the timeout duration
        # or an error is encountered
        with subscriber:
            try:
                streaming_pull_future.result()
            except KeyboardInterrupt:
                streaming_pull_future.cancel()  # Trigger the shutdown.
                streaming_pull_future.result()  # Block until the shutdown is complete.

    else:
        return streaming_pull_future


# --- Publish --- #
def publish(
    topic_name: str, message: bytes, project_id: Optional[str] = None, attrs: dict = {}
) -> str:
    """Publish messages to a Pub/Sub topic.

    Wrapper for `google.cloud.pubsub_v1.PublisherClient().publish()`
    documented at
    https://googleapis.dev/python/pubsub/latest/publisher/api/client.html.

    See also: https://cloud.google.com/pubsub/docs/publisher

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
    subscription_name: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Subscription:
    """Create a subscription to a Pitt-Google Pub/Sub topic.

    Wrapper for `google.cloud.pubsub_v1.SubscriberClient().create_subscription()`
    documented at
    https://googleapis.dev/python/pubsub/latest/subscriber/api/client.html.

    See also: https://cloud.google.com/pubsub/docs/admin#manage_subs

    Args:
        topic_name: Name of a Pitt-Google Broker Pub/Sub topic to subscribe to.
        project_id: User's GCP project ID. If None, the environment variable
                    GOOGLE_CLOUD_PROJECT will be used. The subscription will be
                    created in this account.
        subscription_name: Name for the user's Pub/Sub subscription. If None,
                           `topic_name` will be used.

    Returns:
        A Pub/Sub `Subscription` instance
    """
    if project_id is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if subscription_name is None:
        subscription_name = topic_name

    subscriber = pubsub_v1.SubscriberClient()
    publisher = pubsub_v1.PublisherClient()

    sub_path = subscriber.subscription_path(project_id, subscription_name)
    topic_path = publisher.topic_path(pgb_project_id, topic_name)
    request = {"name": sub_path, "topic": topic_path}

    with subscriber:
        subscription = subscriber.create_subscription(request=request)

    print(f"Created subscription {subscription.name}")
    print(f"attached to topic {subscription.topic}")

    return subscription


# --- Delete a subscription --- #
def delete_subscription(
    subscription_name: str, project_id: Optional[str] = None
) -> None:
    """Delete a Pub/Sub subscription.

    Wrapper for `google.cloud.pubsub_v1.SubscriberClient().delete_subscription()`
    documented at
    https://googleapis.dev/python/pubsub/latest/subscriber/api/client.html.

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
        subscriber.delete_subscription(request=request)

    print(f"Subscription deleted: {subscription_path}.")


# --- Decode messages --- #
def decode_message(
    msg_bytes: bytes,
    return_alert_as: str = "dict",
) -> Union[
    Union[dict, pd.DataFrame, Table],
    Union[Tuple[dict, dict], Tuple[pd.DataFrame, dict], Tuple[Table, dict]],
]:
    """Decode the message and return in requested format.

    Args:
        msg_bytes: a single alert

        return_alert_as: Format for the returned alert.
            One of "dict" (dictionary), "df" (Pandas DataFrame) or
            "table" (Astropy Table).
            Note that only the "dict" option returns the full packet.
            Using "df" or "table" drops some metadata and the cutouts (if present).

    Returns:
        If the message contains an alert packet only, it is returned in the requested
        format.

        If the message contains an alert packet plus value added products, it is
        returned as a tuple where the first element is the alert packet in the
        requested format, and the second element is the value added products as a dict.
    """
    # decode the message
    try:
        # decode message with avro encoding
        # may come from topic ztf-alerts or ztf-loop
        alert_dict, va_dict = _decode_avro_alert(msg_bytes)
    except ValueError:
        try:
            # decode message with json encoding
            # may come from ztf-alerts_pure, ztf-exgalac_trans, or ztf-salt2
            alert_dict, va_dict = _decode_json_msg(msg_bytes)
        except UnicodeDecodeError:
            _raise_decode_error()
        except json.JSONDecodeError:
            _raise_decode_error()

    # cast the alert to the requested type
    if return_alert_as == "dict":
        alert = alert_dict
    elif return_alert_as == "df":
        alert = _alert_dict_to_dataframe(alert_dict)
    elif return_alert_as == "table":
        alert = _alert_dict_to_table(alert_dict)
    else:
        errmsg = f"Received return_alert_as = {return_alert_as}, which is invalid"
        raise ValueError(errmsg)

    # package the object(s) to return
    if va_dict is None:
        rtn = alert
    else:
        rtn = (alert, va_dict)

    return rtn


def _decode_avro_alert(
    alert_bytes: bytes,
) -> Union[Tuple[dict, dict], Tuple[dict, None]]:
    # extract the alert data
    with BytesIO(alert_bytes) as fin:
        alert_dicts = [r for r in reader(fin)]  # list of dicts
    # ZTF alerts are expected to contain one dict in the list
    assert len(alert_dicts) == 1
    alert_dict = alert_dicts[0]

    # these streams do not have value added products
    va_dict = None

    return alert_dict, va_dict


def _decode_json_msg(
    msg_bytes: bytes
) -> Union[Tuple[dict, dict], Tuple[dict, None]]:
    # decode to a dict
    dict_str = msg_bytes.decode("UTF-8")
    dic = json.loads(dict_str)

    # separate alert from value added
    if "alert" in dic.keys():  # value added products are included in the msg
        alert_dict = dic.pop("alert")
        va_dict = dic

    else:  # msg is just the alert
        alert_dict = dic
        va_dict = None

    return alert_dict, va_dict


def _strip_cutouts_ztf(alert_dict: dict) -> dict:
    """Drop the cutouts from the alert dictionary.

    Args:
        alert_dict: ZTF alert formated as a dict
    Returns:
        `alert_data` with the cutouts (postage stamps) removed
    """
    cutouts = ["cutoutScience", "cutoutTemplate", "cutoutDifference"]
    alert_stripped = {k: v for k, v in alert_dict.items() if k not in cutouts}
    return alert_stripped


def _alert_dict_to_dataframe(alert_dict: dict) -> pd.DataFrame:
    """Package a ZTF alert dictionary into a dataframe.

    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    dfc = pd.DataFrame(alert_dict["candidate"], index=[0])
    df_prv = pd.DataFrame(alert_dict["prv_candidates"])
    df = pd.concat([dfc, df_prv], ignore_index=True, sort=True)
    df = df[dfc.columns]  # return to original column ordering

    # we'll attach some metadata--note this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    df.objectId = alert_dict["objectId"]
    return df


def _alert_dict_to_table(alert_dict: dict) -> Table:
    """Package a ZTF alert dictionary into an Astopy Table."""
    rows = [alert_dict["candidate"]] + alert_dict["prv_candidates"]
    table = Table(rows=rows)
    table.meta["comments"] = f"ZTF objectId: {alert_dict['objectId']}"
    return table


def _raise_decode_error():
    errmsg = (
        "Unable to decode the message. "
        "It does not seem to be of an expected type."
    )
    raise ValueError(errmsg)
