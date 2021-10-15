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

    def __init__(self, subscription_name):
        """Connect to subscription."""
        user_project = PROJECT_ID
        self.database_list = []  # fake db. returned by stream_alerts

        self.client = pubsub_v1.SubscriberClient()

        self.subscription_name = subscription_name
        self.subscription_path = f"projects/{user_project}/subscriptions/{subscription_name}"
        # Topic to connect the subscription to, if it needs to be created.
        # If the subscription already exists but is connected to a different topic,
        # the user will be notified and this topic_path will be updated for consistency.
        self.topic_path = f"projects/{PROJECT_ID}/topics/{subscription_name}"
        self.touch_subscription()

    def stream_alerts(self, callback=None, parameters=None):
        """Execute a streaming pull and process alerts through the `callback`.

        The streaming pull happens in a background thread. A `queue.Queue` is used
        to communicate between threads and enforce the stopping condition(s).

        Args:
            parameters (dict): There must be at least one stopping condition
                               (`max_results` or `timeout`), else the streaming pull
                               will run forever.
                               `max_backlog`
        """
        self.queue = queue.Queue()  # queue for communication between threads
        self.callback = callback if callback is not None else self._callback
        params = self._parameters(parameters)
        self.parameters = params
        # avoid pulling down a large number of alerts that don't get processed
        flow_control = pubsub_v1.types.FlowControl(max_messages=params['max_backlog'])

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

        # Use the queue to count saved messages and
        # stop when we hit a max_messages or timeout stopping condition.
        count = 0
        while True:
            try:
                count += self.queue.get(block=True, timeout=params['timeout'])
            except Empty:
                break
            else:
                self.queue.task_done()
                if params['max_results'] & count >= params['max_results']:
                    break
        self._stop()

        self._log_and_print(f"Saved {count} messages from {self.subscription_path}")

        return self.database_list

    def _parameters(self, parameters):
        defaults = {
            'max_results': None,
            'timeout': 30,
            'max_backlog': 1000,
        }
        if parameters is None:
            parameters = {}
        return {k: parameters.get(k, defaults[k]) for k in defaults.keys()}

    def _stop(self):
        """Shutdown the streaming pull in the background thread gracefully.

        Implemented as a separate function so the developer can quickly shut it down
        if things get out of control during dev. :)
        """
        self.streaming_pull_future.cancel()  # Trigger the shutdown.
        self.streaming_pull_future.result()  # Block until the shutdown is complete.

    def _callback(self, message):
        """Process a single alert; run user filter; save alert; acknowledge msg."""
        params = self.parameters

        # alert_dict = avro_to_dict(message.data)
        # if alert_dict is not None:
        #     if params['save_metadata'] == "yes":
        #         # nest inside the alert so we don't break the broker
        #         alert_dict['metadata'] = self._extract_metadata(message)
        #     self.save_alert(alert_dict)
        #     count = 1
        # else:
        #     count = 0

        self.database_list.append(message)
        count = 1

        # communicate with the main thread
        self.queue.put(count)
        # block until main thread acknowledges so we don't ack msgs that get lost
        if params['max_results'] is not None:
            self.queue.join()  # single background thread => one-in-one-out

        message.ack()

    def _extract_metadata(self, message):
        # TOM wants to serialize this and has trouble with the dates.
        # Just make everything strings for now.
        return {
            "message_id": message.message_id,
            "publish_time": str(message.publish_time),
            # attributes includes the originating 'kafka.timestamp' from ZTF
            "attributes": {k: str(v) for k, v in message.attributes.items()},
        }

    def _lighten_alert(self, alert_dict):
        keep_fields = {
            "top-level": ["objectId", "candid", ],
            "candidate": ["jd", "ra", "dec", "magpsf", "classtar", ],
        }
        alert_lite = {k: alert_dict[k] for k in keep_fields["top-level"]}
        alert_lite.update(
            {k: alert_dict["candidate"][k] for k in keep_fields["candidate"]}
        )
        return alert_lite

    def save_alert(self, alert):
        """Save the alert to a database."""
        self.database_list.append(alert)  # fake database for demo

    def touch_subscription(self):
        """Make sure the subscription exists and we can connect.

        If the subscription doesn't exist, try to create one (in the user's project)
        that is attached to a topic of the same name in the Pitt-Google project.
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
            self._log_and_print(f'Deleted subscription: {self.subscription_path}')

    def _log_and_print(self, msg, severity="INFO"):
        # self.logger.log_text(msg, severity=severity)
        print(msg)
