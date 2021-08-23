#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Collect and store metadata from Pub/Sub subscriptions."""


import argparse
from google.cloud import logging
import json
import pandas as pd
import time
from typing import Tuple, Union

from broker_utils import gcp_utils, schema_maps


# connect to the logger
logging_client = logging.Client()
log_name = "process-pubsub-counters"  # same log for all broker instances
logger = logging_client.logger(log_name)


def _resource_names(survey: str, testid: Union[str, bool]):
    """Name all the resources used in this script."""
    names = {}

    # bigquery table
    if not testid:
        names["bq_table"] = f"{survey}_alerts.metadata"
    else:
        names["bq_table"] = f"{survey}_alerts_{testid}.metadata"

    # pubsub names as {topic name stub: full subscription name}
    name_stubs = [
        "alert_avros",
        "alerts",
        "alerts_pure",
        "exgalac_trans",
        "salt2",
        "SuperNNova",
    ]
    if not testid:
        names["pubsub"] = {ns: f"{survey}-{ns}-counter" for ns in name_stubs}
    else:
        names["pubsub"] = {ns: f"{survey}-{ns}-counter-{testid}" for ns in name_stubs}
        # subscriptions = [f'{survey}-{ns}-counter-{testid}' for ns in name_stubs]

    return names


def run(survey: str, testid: Union[str, bool], batch_size: int):
    """Collect and store all metadata in the Pub/Sub counters."""
    collector = MetadataCollector(survey, testid, batch_size)
    collector.collect_and_store_all_metadata()


class MetadataCollector:
    """Collects metadata from the Pub/Sub counters and stores it in BigQuery.

    Pub/Sub counter subscriptions and other resources are named at the script level
    in _resource_names().

    Extracted metadata generally includes the message's message_id and publish_time,
    and the custom metadata attributes set by the broker
    (e.g., the DIA ids for the object and source).
    Additional metadata includes the info about the original Kafka stream and
    the Avro file storage.

    The DIA ids are used to join the metadata from all counters,
    and the result is stored to the BigQuery "metadata" table.

    The messages coming from the main "alerts" stream require special handling because
    the Consumer, from which they originate, does not open the messages and therefore
    it cannot attach the DIA ids as metadata.
    To fix this, the Cloud Function that stores the alert Avro files has been
    configured to grab and store the only unique identifier available, the
    Pub/Sub message_id, which is used here to associate "alerts" stream messages with
    DIA ids.

    Any collected attributes that do not have a matching column in the BigQuery table
    schema are dropped.
    """

    def __init__(self, survey: str, testid: Union[str, bool], batch_size: int):
        """Initialize a MetadataCollector.

        Args:
            survey: The broker instance's `survey` keyword. Names the resources.
            testid: The broker instance's `testid` keyword. Names the resources.
            batch_size: Maximum number of messages to pull and process in a batch.
        """
        self.batch_size = batch_size
        self.metadata_dfs_dict = {}  # one df per subscription
        self.metadata_df = None  # all subscriptions
        self.schema_map = schema_maps.load_schema_map(survey, testid)

        names = _resource_names(survey, testid)
        self.bq_table = names["bq_table"]
        self.pubsub_names = names["pubsub"]

    def collect_and_store_all_metadata(self):
        """Entry point for the MetadataCollector."""
        # collect it
        self._collect_all_metadata()  # populate self.metadata_dfs_dict
        # reorganize it
        self._join_metadata()  # populate self.metadata_df
        # store it
        self._load_metadata_to_bigquery()

    def _collect_all_metadata(self):
        # iterate subscriptions,
        # call SubscriptionMetadataCollector to pull the messages and extract metadata,
        # store the result in self.metadata_dfs_dict
        self.metadata_dfs_dict = {}

        for topic_stub, sub_name in self.pubsub_names.items():
            print(f"processing {sub_name}")

            # generate a df of metadata from all messages in the subscription
            sub_collector = SubscriptionMetadataCollector(
                (topic_stub, sub_name), self.schema_map, self.batch_size
            )
            sub_collector.pull_and_process_messages()

            # stash the subscription's metadata
            if sub_collector.metadata_df is not None:
                self.metadata_dfs_dict[topic_stub] = sub_collector.metadata_df

    def _join_metadata(self):
        # all subscription dfs are indexed by [objectId, sourceId]
        # except the alerts df... fix it
        self._add_ids_to_alerts_stream()

        # join the subscription dfs on index
        alerts = self.metadata_dfs_dict["alerts"]
        allothers = [df for t, df in self.metadata_dfs_dict.items() if t != "alerts"]
        self.metadata_df = alerts.join(allothers, how="outer")

    def _add_ids_to_alerts_stream(self):
        """Add objectId and sourceId to alerts stream metadata.

        The messages coming from the main "alerts" stream require special handling
        because the Consumer, from which they originate, does not open the messages and
        therefore it cannot attach the DIA ids as metadata.

        To fix this, the Cloud Function that stores the alert Avro files has been
        configured to grab and store the only unique identifier available, the
        Pub/Sub message_id, which is used here to associate "alerts" stream messages
        with DIA ids.
        """
        # column names
        oid = self.schema_map["objectId"]
        sid = self.schema_map["sourceId"]
        msg_id_long = "file_origin_message_id__alert_avros"
        msg_id = "message_id"

        # get all the ids from the alert_avros metadata
        df_avros = self.metadata_dfs_dict["alert_avros"].reset_index()
        df_avros[msg_id] = df_avros[msg_id_long].astype(int)
        df_avros = df_avros[[oid, sid, msg_id]]  # drop the other columns
        df_avros = df_avros.set_index(msg_id)
        df_avros = df_avros[~df_avros.index.duplicated(keep="first")]  # drop duplicates

        # add the ids to the alerts metadata
        df_alerts = self.metadata_dfs_dict["alerts"].copy(deep=True)
        df_alerts[oid] = df_avros[oid]
        df_alerts[sid] = df_avros[sid]

        # log and drop messages we can't identify
        null_sid = df_alerts[sid].isnull()  # series of bools
        null_msg_ids = df_alerts[null_sid].index
        if len(null_msg_ids) > 0:
            msg = (
                f"Dropping {len(null_msg_ids)} messages from alerts stream "
                f"because they cannot be matched to a {sid}. "
                f"Their Pub/Sub message ids are: {null_msg_ids.tolist()}"
            )
            logger.log_text(msg, severity='DEBUG')
        df_alerts.drop(index=null_msg_ids, inplace=True)

        # set the new index and return
        self.metadata_dfs_dict["alerts"] = df_alerts.set_index([oid, sid])

    def _load_metadata_to_bigquery(self):
        # by default, conforms the dataframe to the table schema
        # i.e., converts dtypes and drops extra columns
        gcp_utils.load_dataframe_bigquery(
            self.bq_table, self.metadata_df.reset_index(), logger=logger
        )


class SubscriptionMetadataCollector:
    """Collects metadata from a single Pub/Sub counter.

    Extracted metadata generally includes the message's message_id and publish_time,
    and the custom metadata attributes set by the broker
    (e.g., the DIA ids for the object and source).
    Additional metadata includes the info about the original Kafka stream and
    the Avro file storage.

    The messages coming from the "alert_avros" stream receive special handling
    to extract *file* metadata, which gets packaged into the Pub/Sub message body.
    """

    def __init__(
        self, pubsub_names: Tuple[str, str], schema_map: dict, batch_size: int = 500
    ):
        """Initialize a SubscriptionMetadataCollector.

        Args:
            pubsub_names: Pub/Sub stream to be processed, in the format
                          (topic name stub, full subscription name).
            schema_map: Mapping between survey schema and broker's generic schema.
            batch_size: Maximum number of messages to pull and process in a batch.
        """
        self.batch_size = batch_size
        self.metadata_df = None
        self.metadata_dicts_list = []
        self.schema_map = schema_map
        self.topic_stub, self.subscription = pubsub_names

    def pull_and_process_messages(self):
        """Entry point for the SubscriptionMetadataCollector."""
        # collect the metadata
        self._pull_messages_and_extract_metadata()  # populate self.metadata_dicts_list

        # for debugging: write to file in case next step fails
        # self._stash_dicts_to_json_file()

        # create dataframe with proper index and column names
        if len(self.metadata_dicts_list) > 0:
            self._package_metadata_into_df()  # populate self.metadata_df

    def _pull_messages_and_extract_metadata(self):
        # pull and process messages in batches
        # using the callback self._extract_metadata().
        # populate self.metadata_dicts_list

        # pull. assume there are no more msgs when 2 successive calles return nothing.
        # if this turns out to be insufficient, use the Pub/Sub monitoring metrics here:
        # https://cloud.google.com/monitoring/api/metrics_gcp#gcp-pubsub
        total_num_processed = 0
        num_in_batch = 1  # >0 to start the loop
        while num_in_batch > 0:
            num_in_batch = gcp_utils.pull_pubsub(
                self.subscription,
                max_messages=self.batch_size,
                msg_only=False,
                callback=self._extract_metadata,
                return_count=True,
            )

            if num_in_batch == 0:  # wait, then try one more time
                time.sleep(10)
                num_in_batch = gcp_utils.pull_pubsub(
                    self.subscription,
                    max_messages=self.batch_size,
                    msg_only=False,
                    callback=self._extract_metadata,
                    return_count=True,
                )

            print(f"\tfinished batch of {num_in_batch}")
            total_num_processed = total_num_processed + num_in_batch

        # log the total
        msg = (
            f"Pulled {total_num_processed} messages from "
            f"{self.subscription} and extracted metadata."
        )
        logger.log_text(msg, severity="INFO")

    def _extract_metadata(self, received_message):
        # process a pubsub message and extract metadata
        message = received_message.message

        # collect the custom metadata; e.g., DIA ids
        metadata = {**message.attributes}

        # collect other metadata
        metadata["message_id"] = message.message_id
        metadata["publish_time"] = self._package_publish_time(message.publish_time)

        # handle uniqueness of messages coming from the alert_avros bucket
        if "alert_avros-counter" in self.subscription:
            metadata = self._package_alert_avros_metadata(message.data, metadata)

        self.metadata_dicts_list.append(metadata)

        # for now, we assume everything went fine... update this if problems arise
        success = True
        return success

    def _stash_dicts_to_json_file(self):
        # for debugging
        fname = f"metadata/{self.subscription}.json"
        with open(fname, "w") as fout:
            json.dump(self.metadata_dicts_list, fout, allow_nan=True)

    def _package_metadata_into_df(self):
        # cast to a dataframe and set the index and columns
        oid = self.schema_map["objectId"]  # survey-specific field name for the objectId
        sid = self.schema_map["sourceId"]  # survey-specific field name for the sourceId

        # cast the collected metadata to a df
        df = pd.DataFrame(self.metadata_dicts_list)

        # set the index with explicit types
        if (oid in df.columns) and (sid in df.columns):
            df = df.astype({oid: str, sid: str})
            df = df.set_index([oid, sid])
        else:
            # currently this is just the "alerts" stream
            # and is handled in MetadataCollector._add_ids_to_alerts_stream()
            df = df.astype({"message_id": int}).set_index("message_id")

        # attach topic name stub to column names, separated by double underscore
        df.rename(columns=lambda x: f"{x}__{self.topic_stub}", inplace=True)

        # format column names; BigQuery accepts only letters, numbers, and underscores
        df.rename(columns=lambda x: x.replace("-", "_"), inplace=True)
        df.rename(columns=lambda x: x.replace(".", "_"), inplace=True)

        self.metadata_df = df

    def _package_publish_time(self, publish_time):
        # publish_time timestamp is given as two ints: seconds and nanoseconds
        # package it into a single number

        # preserve zero padding
        tmpnanos = f"{publish_time.nanos*1e-9}".split(".")[1][:9]

        # concat. use string type to ensure exact representation
        pubtime = f"{publish_time.seconds}.{tmpnanos}"

        return pubtime

    def _package_alert_avros_metadata(self, msg_data, msg_metadata):
        # clarify the metadata names
        # extract *file* metadata stored in the message body

        # rename field for clarity and to avoid name collision with DIA objectId
        msg_metadata["filename"] = msg_metadata.pop("objectId")

        # extract the file's custom metadata set in the ps_to_gcs cloud fnc
        file_metadata = json.loads(msg_data.decode("UTF-8"))
        file_custom_metadata = file_metadata["metadata"]

        metadata = {**msg_metadata, **file_custom_metadata}

        return metadata


if __name__ == "__main__":  # noqa
    parser = argparse.ArgumentParser()
    # survey
    parser.add_argument(
        "--survey",
        dest="survey",
        default="ztf",
        help="The broker instance's `survey` keyword. Names the resources.\n",
    )
    # testid
    # when calling this script, use one of `--testid=<mytestid>` or `--production`
    parser.add_argument(
        "--testid",  # set testid = <mytestid>
        dest="testid",
        default="test",
        help="The broker instance's `testid` keyword. Names the resources\n",
    )
    parser.add_argument(
        "--production",  # set testid = False
        dest="testid",
        action="store_false",
        default="test",
        help="Sets `testid=False`. Use for broker production instances.\n",
    )
    parser.add_argument(
        "--batch_size",
        dest="batch_size",
        default=500,
        help="Maximum number of Pub/Sub messages to pull per call.",
    )

    known_args, __ = parser.parse_known_args()

    run(known_args.survey, known_args.testid, int(known_args.batch_size))
