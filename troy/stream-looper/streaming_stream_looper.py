#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Consumer and Publisher classes run the stream looper.

Taken from `ConsumerStreamPython`, written for TOM Toolkit.
"""

# from concurrent.futures.thread import ThreadPoolExecutor
from google.cloud import pubsub_v1
# from google.cloud.pubsub_v1.subscriber.scheduler import ThreadScheduler
# from google.cloud import logging as gc_logging
import queue
import time


PITTGOOGLE_PROJECT_ID = "ardent-cycling-243415"
TOPIC_NAME = 'ztf-loop'
SUBSCRIPTION_NAME = 'ztf-alerts-reservoir'

# LOGGER = gc_logging.Client().logger("stream-looper")

MAX_MESSAGES = 10
QUEUE = queue.Queue(maxsize=MAX_MESSAGES)  # queue for communication between threads


class Publisher:
    """."""

    def __init__(self, topic_name, subscription_name):
        """Run a Consumer; publish messages to topic_name."""
        self.client = pubsub_v1.PublisherClient()
        self.topic_path = f"projects/{PITTGOOGLE_PROJECT_ID}/topics/{topic_name}"

        self.consumer = ConsumerStreamPython(subscription_name)

    def run_looper(self):
        """Run looper."""
        sleep = 1

        self.consumer.stream_alerts()

        while True:
            try:
                msg_data, attributes = QUEUE.get(block=True)
                future = self.client.publish(
                    self.topic_path, msg_data, **attributes
                )  # non blocking
                future.add_done_callback(self._callback)  # check for errors in bkgd thread
                QUEUE.task_done()
                time.sleep(sleep)

            except:
                self.consumer._stop()
                break

    def _callback(self, future):
        # Publishing failures are automatically retried,
        # except for errors that do not warrant retries.
        message_id = future.result()  # raises an exception if publish ultimately failed
        # print(message_id)


class ConsumerStreamPython:
    """Consumer class to manage Pub/Sub connections and work with messages."""

    def __init__(self, subscription_name):
        """Authenticate user; create client; set subscription path; check connection."""
        self.client = pubsub_v1.SubscriberClient()

        # subscription
        self.subscription_name = subscription_name
        self.subscription_path = f"projects/{PITTGOOGLE_PROJECT_ID}/subscriptions/{subscription_name}"

    def stream_alerts(self, parameters=None):
        """Execute a streaming pull and process alerts through the `callback`."""
        flow_control = pubsub_v1.types.FlowControl(max_messages=MAX_MESSAGES)
        # start pulling and processing msgs using the callback, in a background thread
        self.streaming_pull_future = self.client.subscribe(
            self.subscription_path,
            self.callback,
            flow_control=flow_control,
            # scheduler=self.scheduler,
            # await_callbacks_on_shutdown=True,
        )

    def _stop(self):
        """Shutdown the streaming pull in the background thread gracefully.

        Implemented as a separate function so the developer can quickly shut it down
        if things get out of control during dev. :)
        """
        self.streaming_pull_future.cancel()  # Trigger the shutdown.
        self.streaming_pull_future.result()  # Block until the shutdown is complete.

    def callback(self, message):
        """Process a single alert; run user filter; save alert; acknowledge Pub/Sub msg.

        Used as the callback for the streaming pull.
        """
        QUEUE.put((message.data, message.attributes), block=True)
        message.ack()

    def _log_and_print(self, msg, severity="INFO"):
        # LOGGER.log_text(msg, severity=severity)
        print(msg)


if __name__ == "__main__":  # noqa
    Publisher(TOPIC_NAME, SUBSCRIPTION_NAME).run_looper()
