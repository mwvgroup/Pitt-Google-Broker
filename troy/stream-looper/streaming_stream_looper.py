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


class StreamLooper:
    """."""

    def __init__(self, topic_name, subscription_name):
        """Run a Consumer; publish messages to topic_name."""
        self.subclient = pubsub_v1.SubscriberClient()
        self.subscription_path = f"projects/{PITTGOOGLE_PROJECT_ID}/subscriptions/{subscription_name}"
        self.pubclient = pubsub_v1.PublisherClient()
        self.topic_path = f"projects/{PITTGOOGLE_PROJECT_ID}/topics/{topic_name}"

        MAX_MESSAGES = 5
        self.queue = queue.Queue(maxsize=MAX_MESSAGES)

        MAX_BACKLOG = 50
        self.flow_control = pubsub_v1.types.FlowControl(max_messages=MAX_BACKLOG)

    def run_looper(self):
        """Run looper."""
        sleep = 1

        self.pull_subscription()

        while True:
            try:
                self.publish_topic()
                time.sleep(sleep)

            except:
                self._stop()
                raise
                break

    def pull_subscription(self, parameters=None):
        """Execute a streaming pull and process alerts through the `callback`."""
        # start pulling and processing msgs using the callback, in a background thread
        self.streaming_pull_future = self.subclient.subscribe(
            self.subscription_path,
            self.sub_callback,
            flow_control=self.flow_control,
            # scheduler=self.scheduler,
            # await_callbacks_on_shutdown=True,
        )

    def publish_topic(self):
        """."""
        msg_data, attributes = self.queue.get(block=True)
        future = self.pubclient.publish(
            self.topic_path, msg_data, **attributes
        )  # non blocking
        # check for errors in bkgd thread
        # future.add_done_callback(self.pub_callback)
        future.result()  # raises an exception if publish ultimately failed
        self.queue.task_done()

    def pub_callback(self, future):
        """."""
        # Publishing failures are automatically retried,
        # except for errors that do not warrant retries.
        message_id = future.result()  # raises an exception if publish ultimately failed
        # print(message_id)

    def sub_callback(self, message):
        """Process a single alert; run user filter; save alert; acknowledge Pub/Sub msg.

        Used as the callback for the streaming pull.
        """
        self.queue.put((message.data, message.attributes), block=True)
        message.ack()

    def _stop(self):
        """Shutdown the streaming pull in the background thread gracefully.

        Implemented as a separate function so the developer can quickly shut it down
        if things get out of control during dev. :)
        """
        self.streaming_pull_future.cancel()  # Trigger the shutdown.
        self.streaming_pull_future.result()  # Block until the shutdown is complete.

    def _log_and_print(self, msg, severity="INFO"):
        # LOGGER.log_text(msg, severity=severity)
        print(msg)


if __name__ == "__main__":  # noqa
    StreamLooper(TOPIC_NAME, SUBSCRIPTION_NAME).run_looper()
