#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``data_utils`` module contains common functions used to manipulate
survey and broker data.
"""

import datetime
import os
from pathlib import Path

import numpy as np

from .gcp_utils import pull_pubsub
from .data_utils import load_alert, idUtils


def local_alerts(survey=None, adir=None):
    """Return a generator of paths to Avro files in the directory `adir`."""
    if not adir:
        adir = Path(os.getenv(f"ALERT_DIR_{survey.upper()}"))
    return (p for p in adir.glob('**/*.avro'))


class TestAlert:
    """Functions to work with alerts for testing."""

    def __init__(self, path, schema_map):
        """."""
        self.path = path
        self.data = dict(
            dict=load_alert(path, 'dict', schema_map=schema_map, drop_cutouts=True),
            bytes=load_alert(path, 'bytes'),
        )

        id_utils = idUtils(schema_map)
        self.id_keys = id_utils.get_id_keys()
        # self.objectId_key = get_key("objectId", schema_map)
        # self.sourceId_key = get_key("sourceId", schema_map)
        self.ids = id_utils.get_ids(alert_dict=self.data["dict"])
        # self.objectId = get_value("objectId", self.data["dict"], schema_map)
        # self.sourceId = get_value("sourceId", self.data["dict"], schema_map)

    def create_msg_payload(self, publish_as='json', mock=None):
        """Create a Pub/Sub message payload."""
        atype = {"json": "dict", "avro": "bytes"}  # alert format
        alert = self.data[atype[publish_as]]
        mock_results = self.create_mock_results(mock)

        if publish_as == "avro":
            payload = alert
        else:
            payload = dict(alert=alert, **mock_results)

        return payload

    def create_mock_results(self, modules=None):
        """Create mock results for a pipeline module."""
        mock_results = dict()

        if modules and "SuperNNova" in modules:
            prob_class1 = np.random.uniform()
            mock_results["SuperNNova"] = {
                self.id_keys.objectId: self.ids.objectId,
                self.id_keys.sourceId: self.ids.sourceId,
                "prob_class0": 1-prob_class1,
                "prob_class1": prob_class1,
                "predicted_class": round(prob_class1),
            }

        return mock_results

    def create_msg_attrs(self):
        """Return a dictionary of mock attributes to be attached to the message."""
        # create int POSIX timestamps in microseconds
        now = datetime.datetime.now(datetime.timezone.utc)
        tkafka = int(now.timestamp() * 1e6)
        # to convert back: datetime.datetime.fromtimestamp(tkafka / 1e6)
        tingest = int((now + datetime.timedelta(seconds=0.345678)).timestamp() * 1e6)
        attrs = {
            self.id_keys.objectId: str(self.ids.objectId),
            self.id_keys.sourceId: str(self.ids.sourceId),
            "kafka.timestamp": str(tkafka),
            "ingest.timestamp": str(tingest),
        }
        return attrs

    @staticmethod
    def guess_publish_format(topic):
        """Use the topic to guess the format that the message is expected to be in."""
        avro_topics = ["alerts"]  # all others are json
        try:
            topic_name_stub = topic.split('-')[1]
        except IndexError:
            topic_name_stub = topic
        publish_as = "avro" if topic_name_stub in avro_topics else "json"
        return publish_as


class TestValidator:
    """Functions to validate an integration test."""

    def __init__(self, subscrip, published_alert_ids, schema_map, max_pulls=3):
        """Initialize variables."""
        self.subscrip = subscrip
        self.published_alert_ids = published_alert_ids
        self.id_utils = idUtils(schema_map)
        self.max_pulls = max_pulls

    def pull_and_compare_ids(self):
        """Pull the subscription and validate that ids match the published alerts."""
        pulled_msg_ids = self._pull()

        # _pull() gets the ids from the message attributes which are always strings.
        # convert the published_alert_ids to the same type.
        published_alert_ids = [
            self.id_utils.ids_to_strings(ids) for ids in self.published_alert_ids
        ]

        # compare with published alerts
        diff = set(published_alert_ids).difference(set(pulled_msg_ids))
        success = len(diff) == 0
        fmsgsub = f"The message ids pulled from subscription {self.subscrip}"
        if success:
            print(f"Success! {fmsgsub} match the input.")
        else:
            print(f"Something went wrong. {fmsgsub}  do not match the input.")

        return (success, pulled_msg_ids)

    def _pull(self):
        pulled_msg_ids, i = [], 0
        while len(pulled_msg_ids) < len(self.published_alert_ids):
            max_messages = len(self.published_alert_ids) - len(pulled_msg_ids)
            msgs = pull_pubsub(
                self.subscrip, max_messages=max_messages, msg_only=False
            )
            pulled_msg_ids += self._extract_ids(msgs)

            i += 1
            if i >= self.max_pulls:
                break

        return pulled_msg_ids

    def _extract_ids(self, msgs):
        pulled_msg_ids = [
            self.id_utils.get_ids(attrs=msg.message.attributes) for msg in msgs
        ]
        return pulled_msg_ids
