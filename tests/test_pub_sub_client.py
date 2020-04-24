"""This file provides tests for the ``broker.pub_sub_client`` module."""

import os
from pathlib import Path
import unittest
from deepdiff import DeepDiff

from broker import pub_sub_client as psc
from broker.alert_ingestion.gen_valid_schema import _load_Avro

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
test_alerts_dir = Path(__file__).parent / 'test_alerts'
test_alert_path = test_alerts_dir / 'ztf_3.3_1154308030015010004.avro'

topic_name = 'test_alerts_PS_publish'
subscription_name = 'test_alerts_PS_subscribe'


class TestPubSub(unittest.TestCase):
    """Test the functions in ``message_service`` for correct output,
    given an input.
    """

    def test_publish_pubsub(self):
        """ Tests that the generic publish_pubsub() wrapper function works by
        publishing the data from a test alert to a PS stream.
        """
        with open(test_alert_path, 'rb') as f:
            sample_alert_data = f.read()

        future_result = psc.message_service.publish_pubsub(topic_name, sample_alert_data)
        # future_result should be the message ID as a string.
        # if the job fails, future.results() raises an exception
        # https://googleapis.dev/python/pubsub/latest/publisher/api/futures.html

        self.assertIs(type(future_result), str)

    def test_input_match_output(self):
        """Publish an alert via ``publish_alerts`` and retrieve the message
        via ``subscribe_alerts``.
        Check that the input alert matches the decoded output alert.
        """

        with open(test_alert_path, 'rb') as f:
            sample_alert_data = f.read()

        psc.message_service.publish_pubsub(topic_name, sample_alert_data)

        message = psc.message_service.subscribe_alerts(subscription_name, max_alerts=1)

        self.assertEqual(DeepDiff(sample_alert_data[0], message[0]), {})
