#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Consumer class to pull Pub/Sub messages via a Python client, and work with data.

Pub/Sub Python Client docs: https://googleapis.dev/python/pubsub/latest/index.html

Basic workflow:

.. code:: python

    consumer = Consumer(subscription_name)

    alert_dicts_list = consumer.stream_alerts(
        lighten_alerts=True,
        callback=callback,
        parameters=parameters,
    )
    # alerts are processed and saved in real time. the list is returned for convenience.
"""

# from concurrent.futures.thread import ThreadPoolExecutor
# from django.conf import settings
from google.api_core.exceptions import NotFound
from google.cloud import pubsub_v1

# from google.cloud.pubsub_v1.subscriber.scheduler import ThreadScheduler
from google.cloud import logging as gc_logging

# from google_auth_oauthlib.helpers import credentials_from_session
# from requests_oauthlib import OAuth2Session
import queue
from queue import Empty

from .cast_types import avro_to_dict


PROJECT_ID = "ardent-cycling-243415"


class Consumer:
    """Listen to a Pub/Sub stream."""

    def __init__(self, subscription_name, save_fields=None):
        """Connect to subscription."""
        user_project = PROJECT_ID
        self.database_list = []  # fake db. returned by stream_alerts

        self.client = pubsub_v1.SubscriberClient()

        self.subscription_name = subscription_name
        self.subscription_path = (
            f"projects/{user_project}/subscriptions/{subscription_name}"
        )
        # Topic to connect the subscription to, if it needs to be created.
        # If the subscription already exists but is connected to a different topic,
        # the user will be notified and this topic_path will be updated for consistency.
        self.topic_path = f"projects/{PROJECT_ID}/topics/{subscription_name}"
        self.touch_subscription()

        # field names to keep in the unpacked alert_dict
        self._set_save_fields(save_fields)

        # queue for communication between threads. Enforces stopping conditions.
        self.queue = queue.Queue()

    def stream_alerts(self, user_filter=None, user_callback=None, **user_kwargs):
        """Execute a streaming pull and process alerts through the `callback`.

        The streaming pull happens in a background thread. A `queue.Queue` is used
        to communicate between threads and enforce the stopping condition(s).

        Args:
            user_filter (Callable): Used by `callback` to filter alerts before
                                    saving. It should accept a single alert as a
                                    dictionary (flat dict with fields determined by
                                    `save_fields`).
                                    It should return the alert dict if it passes the
                                    filter, else None.

            user_callback (Callable): Used by `callback` to process alerts.
                                      It should accept a single alert as a
                                      dictionary (flat dict with fields determined by
                                      `save_fields`).
                                      It should return True if the processing was
                                      successful; else False.

            kwargs (dict): User's parameters. Should include the parameters
                           defined in `BrokerStreamPython`'s `FilterAlertsForm`.
                           There must be at least one stopping condition
                           (`max_results` or `timeout`), else the streaming pull
                           will run forever.
                           These will also be passed to user_filter and user_callback.
                           Use send_alert_bytes=True and/or send_metadata=True
                           (in order) to have those objects passed to the user_filter
                           and/or user_callback.
        """
        # callback doesn't accept kwargs. set attribute instead.
        kwargs = self._add_default_kwargs(**user_kwargs)
        self.callback_kwargs = {
            "user_filter": user_filter,
            "user_callback": user_callback,
            **kwargs,
        }

        # avoid pulling down a large number of alerts that don't get processed
        flow_control = pubsub_v1.types.FlowControl(max_messages=kwargs["max_backlog"])

        # Google API has a thread scheduler that can run multiple background threads
        # and includes a queue, but I (Troy) haven't gotten it working yet.
        # self.scheduler = ThreadScheduler(ThreadPoolExecutor(max_workers))
        # self.scheduler.schedule(self.callback, lighten_alerts=lighten_alerts)

        # start pulling and processing msgs using the callback, in a background thread
        self.streaming_pull_future = self.client.subscribe(
            self.subscription_path,
            self.callback,
            flow_control=flow_control,
            # scheduler=self.scheduler,
            # await_callbacks_on_shutdown=True,
        )

        try:
            # Use the queue to count saved messages and
            # stop when we hit a max_messages or timeout stopping condition.
            num_saved = 0
            while True:
                try:
                    num_saved += self.queue.get(block=True, timeout=kwargs["timeout"])
                except Empty:
                    break
                else:
                    self.queue.task_done()
                    if kwargs["max_results"] & num_saved >= kwargs["max_results"]:
                        break
            self._stop()

        except (KeyboardInterrupt, Exception):
            self._stop()
            raise

        self._log_and_print(f"Saved {num_saved} messages from {self.subscription_path}")

        return self.database_list

    def _add_default_kwargs(self, **kwargs):
        defaults = {
            "max_results": None,
            "timeout": 30,
            "max_backlog": 1000,
            "return_msg": False,
        }
        if kwargs is None:
            kwargs = {}
        keys = list(set(defaults.keys()).union(set(kwargs.keys())))
        return {k: kwargs.get(k, defaults[k]) for k in keys}

    def _stop(self):
        """Shutdown the streaming pull in the background thread gracefully."""

        self.streaming_pull_future.cancel()  # Trigger the shutdown.
        self.streaming_pull_future.result()  # Block until the shutdown is complete.

    def callback(self, message):
        """Process a single alert; run user filter; save alert; acknowledge Pub/Sub msg.

        Used as the callback for the streaming pull.
        """
        kwargs = self.callback_kwargs

        if kwargs["return_msg"]:
            self._callback_return_full_message(message)
            return

        # unpack
        try:
            alert_dict, metadata_dict = self._unpack(message)
        except Exception as e:
            self._log_and_print(f"Error unpacking message: {e}", severity="DEBUG")
            message.nack()  # nack so message does not leave subscription
            return

        # run user filter
        if kwargs["user_filter"] is not None:
            try:
                alert_dict = kwargs["user_filter"](alert_dict, **kwargs)
            except Exception as e:
                self._log_and_print(f"Error running user_filter: {e}", severity="DEBUG")
                message.nack()
                return

        # run user callback
        if kwargs["user_callback"] is not None:
            # get args for user_callback
            args = []  # requires args are ordered properly here & in user_callback
            if kwargs.get("send_alert_bytes", False):
                args.append(message.data)
            if kwargs.get("send_metadata", False):
                args.append(metadata_dict)
            try:
                # execute user callback
                success = kwargs["user_callback"](alert_dict, *args, **kwargs)  # bool

            except Exception as e:
                success = False
                msg = f"Error running user_callback: {e}"
            else:
                if not success:
                    msg = "user_callback reported it was unsuccessful."
            finally:
                if not success:
                    self._log_and_print(msg, severity="DEBUG")
                    message.nack()
                    return

        if alert_dict is not None:
            # save so stream_alerts can return it, in case the user wants it (broker)
            self.save_alert(alert_dict)

            # communicate with the main thread
            self.queue.put(1)  # 1 alert successfully processed
            # block until main thread acknowledges so we don't ack msgs that get lost
            if kwargs["max_results"] is not None:
                self.queue.join()  # single background thread => one-in-one-out

        else:
            self._log_and_print("alert_dict is None")

        message.ack()

    def _callback_return_full_message(self, message):
        """."""
        kwargs = self.callback_kwargs
        self.database_list.append(message)
        count = 1

        # communicate with the main thread
        self.queue.put(count)
        # block until main thread acknowledges so we don't ack msgs that get lost
        if kwargs["max_results"] is not None:
            self.queue.join()  # single background thread => one-in-one-out

        message.ack()

    def _unpack(self, message):
        alert_dict = avro_to_dict(message.data)  # nested dict with ZTF schema
        # Let's turn this into something closer to Pitt-Google streams after Issue #101
        # https://github.com/mwvgroup/Pitt-Google-Broker/issues/101
        # flatten dict and keep fields in self.save_fields, except metadata
        alert_dict = self._lighten_alert(alert_dict)
        metadata_dict = self._extract_metadata(message)
        return alert_dict, metadata_dict

    def save_alert(self, alert):
        """Save the alert to a database."""
        self.database_list.append(alert)  # fake database for demo

    def _set_save_fields(self, fields=None):
        """Fields to save in the `_unpack` method."""
        if fields is not None:
            self.save_fields = fields
        else:
            self.save_fields = {
                "top-level": [
                    "objectId",
                    "candid",
                ],
                "candidate": [
                    "jd",
                    "ra",
                    "dec",
                    "magpsf",
                    "classtar",
                ],
                "metadata": ["message_id", "publish_time", "kafka.timestamp"],
            }

    def _extract_metadata(self, message):
        # TOM wants to serialize this and has trouble with the dates.
        # Just make everything strings for now.
        # attributes includes Kafka attributes from originating stream:
        # kafka.offset, kafka.partition, kafka.timestamp, kafka.topic
        attributes = {k: str(v) for k, v in message.attributes.items()}
        metadata = {
            "message_id": message.message_id,
            "publish_time": str(message.publish_time),
            **attributes,
        }
        return {k: v for k, v in metadata.items() if k in self.save_fields["metadata"]}

    def _lighten_alert(self, alert_dict):
        alert_lite = {k: alert_dict[k] for k in self.save_fields["top-level"]}
        alert_lite.update(
            {k: alert_dict["candidate"][k] for k in self.save_fields["candidate"]}
        )
        return alert_lite

    def touch_subscription(self):
        """Make sure the subscription exists and we can connect.

        If the subscription doesn't exist, try to create one (in the user's project)
        that is attached to a topic of the same name in the Pitt-Google project.

        Note that messages published before the subscription is created are not
        available.
        """
        try:
            # check if subscription exists
            sub = self.client.get_subscription(subscription=self.subscription_path)

        except NotFound:
            self._create_subscription()

        else:
            self.topic_path = sub.topic
            print(f"Subscription exists: {self.subscription_path}")
            print(f"Connected to topic: {self.topic_path}")

    def _create_subscription(self):
        """Try to create the subscription."""
        try:
            self.client.create_subscription(
                name=self.subscription_path, topic=self.topic_path
            )
        except NotFound:
            # suitable topic does not exist in the Pitt-Google project
            raise ValueError(
                (
                    f"A subscription named {self.subscription_name} does not exist"
                    "in the Google Cloud Platform project "
                    f"{settings.GOOGLE_CLOUD_PROJECT}, "
                    "and one cannot be automatically create because Pitt-Google "
                    "does not publish a public topic with the same name."
                )
            )
        else:
            self._log_and_print(f"Created subscription: {self.subscription_path}")

    def delete_subscription(self):
        """Delete the subscription.

        This is provided for the user's convenience, but it is not necessary and is not
        automatically called.

            - Storage of unacknowledged Pub/Sub messages does not result in fees.

            - Unused subscriptions automatically expire; default is 31 days.
        """
        try:
            self.client.delete_subscription(subscription=self.subscription_path)
        except NotFound:
            pass
        else:
            self._log_and_print(f"Deleted subscription: {self.subscription_path}")

    def _log_and_print(self, msg, severity="INFO"):
        # self.logger.log_text(msg, severity=severity)
        print(msg)
