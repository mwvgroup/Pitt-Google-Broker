#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Classes and functions used for Pitt-Google broker testing."""

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
from typing import NamedTuple, Union

import numpy as np

from .gcp_utils import pull_pubsub
from .data_utils import load_alert, decode_alert
from .types import _AlertIds, AlertIds


logger = logging.getLogger(__name__)


@dataclass
class AlertPaths:
    """Paths to alerts stored locally."""

    def __init__(self, alert_dir: Union[str, Path] = "ztf"):
        """Load path to alerts directory and initialize variables.

        Args:
            alert_dir:
                Either the path to a directory containing alerts or one of the
                following strings.
                "ALERT_DIR" or "alert_dir": The path will be obtained from the
                    environment variable ALERT_DIR.
                "ztf" or "elasticc": The path will be obtained from the environment
                    variable given by ``f"ALERT_DIR_{alert_dir.upper()}"``
        """
        if alert_dir in ["ALERT_DIR", "alert_dir"]:
            self.alert_dir = Path(os.getenv("ALERT_DIR"))
        elif alert_dir in ["ztf", "elasticc"]:
            self.alert_dir = Path(os.getenv(f"ALERT_DIR_{alert_dir.upper()}"))
        else:
            self.alert_dir = Path(alert_dir)

        self.__mygen = None

    def gen(self):
        """Return a new generator of paths to Avro files in self.alert_dir."""
        return (p for p in self.alert_dir.glob("**/*.avro"))

    @property
    def path(self):
        """Return a path to an alert Avro file.

        This can be used to obtain a random path to an alert, or within a loop to
        continuously iterate over paths in the alert directory.

        The returned path is the next one in self._mygen (a path generator maintained
        internally).
        If you want more control (e.g., to ensure that you iterate over all files in
        the directory and/or do not recieve duplicate paths), use ``AlertPaths().gen()``
        instead.
        """
        return next(self._mygen)

    @property
    def _mygen(self):
        """Path generator used by self."""
        if self.__mygen is None:
            self.__mygen = self.gen()
        return self.__mygen


@dataclass
class Mock:
    """Mock data and objects useful for testing the broker."""

    def __init__(self, **kwargs):
        """Initialize attributes.

        kwargs may contain keys:
            modules:
                List of module names to mock.
            test_alert:
                An instance of TestAlert. This will be used to generate appropriate
                mock data (e.g., Pub/Sub message attributes containing the TestAlert's
                alert IDs).
            args and kwargs for TestAlert:
                These will be used to create a new instance of TestAlert.
        """
        self.kwargs = kwargs

        self._modules = kwargs.get("modules")
        self._module_results = None

        self._my_test_alert = kwargs.get("test_alert")
        self._id_tuples = None

        self._attrs = None

        self._cfinput = None

    # modules to mock
    @property
    def modules(self):
        """List of modules for which mock results should be created.

        If this is set manually, self._module_results will be recreated to accommodate.
        """
        return self._modules

    @modules.setter
    def modules(self, value):
        self._modules = value
        # force recreation of other properties
        self._module_results = None

    @modules.deleter
    def modules(self):
        self._modules = None
        # force recreation of other properties
        self._module_results = None

    # mocked module results
    @property
    def module_results(self):
        """Mock results for the pipeline module(s) given by self.modules."""
        if self._module_results is None:
            if self.modules is not None:
                self._module_results = self._generate_module_results()

        return self._module_results

    @module_results.setter
    def module_results(self, value):
        self._module_results = value

    @module_results.deleter
    def module_results(self):
        self._module_results = None

    def _generate_module_results(self):
        results = dict()

        if "SuperNNova" in self.modules:
            results["SuperNNova"] = self._supernnova_results

        self._module_results = results
        return self._module_results

    @property
    def _supernnova_results(self):
        """Return mocked results for SuperNNova module."""
        prob_class1 = np.random.uniform()
        return dict(
            [
                (self.id_keys.objectId, self.ids.objectId),
                (self.id_keys.sourceId, self.ids.sourceId),
                ("prob_class0", 1 - prob_class1),
                ("prob_class1", prob_class1),
                ("predicted_class", round(prob_class1)),
            ]
        )

    @property
    def my_test_alert(self):
        """Instance of TestAlert used by self to generate appropriate data."""
        if self._my_test_alert is None:
            kwargs = dict(self.kwargs)
            path = kwargs.pop("path", AlertPaths().path)
            schema_map = kwargs.pop("schema_map")
            self._my_test_alert = TestAlert(path, schema_map, **kwargs)
        return self._my_test_alert

    @my_test_alert.setter
    def my_test_alert(self, value):
        self._my_test_alert = value
        # force recreation of other properties
        self._id_tuples = None
        self._cfinput = None

    @my_test_alert.deleter
    def my_test_alert(self):
        self._my_test_alert = None
        # force recreation of other properties
        self._id_tuples = None
        self._cfinput = None

    # tuples of mocked alert ID keys and IDs
    @property
    def id_tuples(self):
        """Tuples of alert ID keys and IDs."""
        if self._id_tuples is None:

            if self._my_test_alert is None:
                sid = ("sourceId", f"mocksrc{int(1e9 * np.random.uniform())}")
                oid = ("objectId", f"mockobj{int(1e9 * np.random.uniform())}")

            else:
                sid = (
                    self._my_test_alert.id_keys.sourceId,
                    str(self._my_test_alert.ids.sourceId),
                )
                oid = (
                    self._my_test_alert.id_keys.objectId,
                    str(self._my_test_alert.ids.objectId),
                )

            self._id_tuples = (sid, oid)

        return self._id_tuples

    @id_tuples.setter
    def id_tuples(self, value):
        self._id_tuples = value

    @id_tuples.deleter
    def id_tuples(self):
        self._id_tuples = None

    # mocked attributes
    @property
    def attrs(self):
        """Mock attributes (dict) for a Pub/Sub message."""
        if self._attrs is None:
            sid, oid = self.id_tuples
            # create int POSIX timestamps in microseconds
            now = datetime.now(timezone.utc)
            tkafka = int(now.timestamp() * 1e6)
            # to convert back: datetime.fromtimestamp(tkafka / 1e6)
            tingest = int((now + timedelta(seconds=0.345678)).timestamp() * 1e6)

            self._attrs = dict(
                [
                    sid,
                    oid,
                    ("kafka.topic", "mock_topic_pittgoogle_test"),
                    ("kafka.timestamp", str(tkafka)),
                    ("ingest.timestamp", str(tingest)),
                ]
            )
        return self._attrs

    @attrs.setter
    def attrs(self, value):
        self._attrs = value

    @attrs.deleter
    def attrs(self):
        self._attrs = None

    # mocked Cloud Functions input
    class _CFInput(NamedTuple):
        """Alert data for input to a Cloud Function."""

        msg: dict
        context: NamedTuple

    class _CFContext(NamedTuple):
        """Mock context input for a Cloud Function."""

        event_id = int(1e12 * np.random.uniform())
        timestamp = (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        # event_type = "google.pubsub.topic.publish"
        event_type = "broker_utils.testing.Mock"
        resource = "mock_resource"

    @property
    def cfinput(self):
        """Mock input to a Cloud Function."""
        if self._cfinput is None:

            # return immediately if no schema map was provided
            if self.kwargs.get("schema_map") is None:
                logger.error("A schema map is required to mock Cloud Function input.")
                return

            else:
                self._cfinput = self._CFInput(
                    msg=dict(
                        data=base64.b64encode(self.my_test_alert.msg_payload),
                        attributes=self.my_test_alert.mock.attrs,
                    ),
                    context=self._CFContext(),
                )

        return self._cfinput

    @cfinput.setter
    def cfinput(self, value):
        self._cfinput = value

    @cfinput.deleter
    def cfinput(self):
        self._cfinput = None


@dataclass
class TestAlert:
    """An alert packet and related functions useful for testing the broker."""

    def __init__(self, path, schema_map, **kwargs):
        """Load the alert from `path` and initialize attributes.

        kwargs may contain keys:
            drop_cutouts (bool):
                Wether to drop the image cutouts from the alert.
            serialize (str):
                "avro" or "json". Serialization format of the Pub/Sub message.
            mock (Mock):
                An instance of Mock containing mocked data which should be attached to
                the message.
            mock_modules (List[str]):
                List of modules for which data should be mocked. This will be passed to
                Mock() as keyword argument "modules". This is ignored if an instance of
                Mock is passed using the "mock" keyword argument.
        """
        self.path = path

        abytes = load_alert(path, "bytes")
        adict = decode_alert(
            abytes, drop_cutouts=kwargs.get("drop_cutouts", True), schema_map=schema_map
        )
        self.data = dict(bytes=abytes, dict=adict)

        aids = AlertIds(schema_map, alert_dict=self.data["dict"])
        self.id_keys = aids.id_keys
        self.ids = aids.ids

        self._serialize = kwargs.get("serialize", "json")
        self._msg_payload = None

        self._mock_modules = kwargs.get("mock_modules", None)
        self._mock = kwargs.get("mock", None)

    # message payload
    @property
    def msg_payload(self):
        """Pub/Sub message payload containing the alert and any mocked results."""
        if self._msg_payload is None:
            # create the message payload
            # alert data type appropriate for the format given by self.serialize
            dtype = {"json": "dict", "avro": "bytes"}
            alert = self.data[dtype[self.serialize]]

            if self.serialize == "avro":
                self._msg_payload = alert

                # currently can't publish an Avro serialized message with mock results
                if self.mock_modules is not None:
                    logger.warning(
                        (
                            "The published message will be an Avro serialized alert. "
                            "Mocked results will NOT be attached."
                        )
                    )

            else:
                if self.mock_modules is None:
                    self._msg_payload = alert

                else:
                    self._msg_payload = dict(alert=alert, **self.mock.module_results)

        return self._msg_payload

    # message serialization format
    @property
    def serialize(self):
        """One of "json" or "avro". Determines the format of the published message.

        If this is set manually, self._msg_payload will be recreated to accommodate.
        If this is manually deleted, it will be set to the default ("json") and
        self._msg_payload will be recreated to accommodate.
        """
        return self._serialize

    @serialize.setter
    def serialize(self, value):
        self._serialize = value
        # force recreation of other properties
        self._msg_payload = None

    @serialize.deleter
    def serialize(self):
        self._serialize = "json"
        # force recreation of other properties
        self._msg_payload = None

    @staticmethod
    def guess_serializer(topic):
        """Use the topic to kguess the format that the message is expected to be in."""
        avro_topics = ["alerts"]  # all others are json

        try:
            topic_name_stub = topic.split("-")[1]
        except IndexError:
            topic_name_stub = topic

        serialize = "avro" if topic_name_stub in avro_topics else "json"
        return serialize

    @property
    def mock_modules(self):
        """List of modules for which results should be mocked.

        If this is set manually, self._mock will be recreated to accommodate.
        """
        return self._mock_modules

    @mock_modules.setter
    def mock_modules(self, value):
        self._mock_modules = value
        # force recreation of other properties
        self._mock = None

    @mock_modules.deleter
    def mock_modules(self):
        self._mock_modules = None
        # force recreation of other properties
        self._mock = None

    @property
    def mock(self):
        """Mock data.

        If this is set manually, this will also set self.mock_modules = mock.modules
        """
        if self._mock is None:
            self._mock = Mock(modules=self.mock_modules, test_alert=self)
        return self._mock

    @mock.setter
    def mock(self, value):
        self._mock = value
        # set dependent attributes
        self.mock_modules = value.modules

    @mock.deleter
    def mock(self):
        self._mock = None


@dataclass
class IntegrationTestValidator:
    """Functions to validate an integration test."""

    def __init__(self, subscrip, published_alert_ids, schema_map, **kwargs):
        """Initialize attributes.

        kwargs can include keys:
            max_pulls (int):
                maximum number of times to pull the Pub/Sub subscription
                before quitting.
        """
        self.subscrip = subscrip
        self.max_pulls = kwargs.get("max_pulls", 4)
        self.pulled_msg_ids = None
        self.published_alert_ids = published_alert_ids
        self.unmatched_ids = None
        self.alert_ids = AlertIds(schema_map)  # load once, use to extract all msg IDs

    def run(self):
        """Pull the subscription and validate that ids match the published alerts."""
        self.pulled_msg_ids = self._pull()
        self.success, self.unmatched_ids = self._compare_ids()
        return self.success

    def _pull(self):
        pulled_msg_ids, i = [], 0
        while len(pulled_msg_ids) < len(self.published_alert_ids):
            max_messages = len(self.published_alert_ids) - len(pulled_msg_ids)
            msgs = pull_pubsub(self.subscrip, max_messages=max_messages, msg_only=False)
            if len(msgs) > 0:
                pulled_msg_ids += self._extract_ids(msgs)

            i += 1
            if i >= self.max_pulls:
                break

        return pulled_msg_ids

    def _extract_ids(self, msgs):
        """Extract the alert IDs from msgs.

        This method first guesses whether the IDs should be extracted from message
        attributes or alert filenames by checking the objectId attribute of the first
        message in msgs.
        Background: Messages generated by a GCS bucket contain an attribute called
        objectId which contains the filename of the object (i.e., file) in the bucket
        that triggered the message. This is a name collision with the alert's DIA
        objectId, which broker pipeline modules place in an attribute of the same name.
        """
        oid0 = msgs[0].message.attributes["objectId"]
        oid_is_filename = oid0.split(".")[-1] == "avro"

        if oid_is_filename:
            pulled_msg_ids = [
                self.alert_ids.extract_ids(filename=msg.message.attributes["objectId"])
                for msg in msgs
            ]

        else:
            pulled_msg_ids = [
                self.alert_ids.extract_ids(attrs=msg.message.attributes) for msg in msgs
            ]

        return pulled_msg_ids

    def _compare_ids(self):
        idsout = set(self.pulled_msg_ids)
        # self._pull() gets the ids from the message attributes or filenames,
        # which are always strings.
        # convert the published_alert_ids to the same type.
        idsin = set(
            [_AlertIds(*[str(id) for id in ids]) for ids in self.published_alert_ids]
        )

        # compare ID sets
        unmatched_ids = idsout.symmetric_difference(idsin)
        success = len(unmatched_ids) == 0

        # log results
        tmp = f"The message IDs pulled from subscription {self.subscrip}"
        if success:
            logger.info(f"Success! {tmp} match the input.")
        else:
            logger.warning(f"Something went wrong. {tmp} do not match the input.")

        # warn if idsout contains IDs that were not published
        if len(idsout.difference(idsin)) > 0:
            logger.warning(
                (
                    "Some IDs were pulled that were not reported as published. "
                    "You may want to purge the subcription using\n"
                    f"\tbroker_utils.gcp_utils.purge_subscription({self.subscrip})\n"
                    "and run the test again."
                )
            )

        return success, unmatched_ids
