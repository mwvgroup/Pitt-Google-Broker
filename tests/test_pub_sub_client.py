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


class TestPubSub(unittest.TestCase):
    """Test the functions in ``message_service`` for correct output,
    given an input.
    """

    def test_input_match_output(self):
        """Publish an alert via ``publish_alerts`` and retrieve the message
        via ``subscribe_alerts``.
        Check that the input alert matches the decoded output alert.
        """

        topic_name = 'test_alerts_PS_publish'
        subscription_name = 'test_alerts_PS_subscribe'
        sample_alert_schema, sample_alert_data = _load_Avro(str(test_alert_path))

        psc.message_service.publish_alerts(PROJECT_ID, topic_name, sample_alert_data)

        message = psc.message_service.subscribe_alerts(PROJECT_ID, subscription_name, max_alerts=1)

        self.assertEqual(DeepDiff(sample_alert_data[0], message[0]), {})
