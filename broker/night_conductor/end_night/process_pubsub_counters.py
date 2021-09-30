#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Collect and store metadata from Pub/Sub subscriptions."""


import argparse
from google.cloud import bigquery, logging
import json
import numpy as np
import pandas as pd
import time
from typing import List, Optional, Tuple, Union

from broker_utils import gcp_utils, schema_maps


project_id = "ardent-cycling-243415"

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
    # table column names
    table = bigquery.Client().get_table(names["bq_table"])
    names["bq_table_cols"] = [s.name for s in table.schema]

    # pubsub names as {topic name stub: full subscription name}
    name_stubs = [
        "alerts",
        "BigQuery",
        "alert_avros",
        "alerts_pure",
        "exgalac_trans",
        "salt2",
        "exgalac_trans_cf",
        "SuperNNova",
    ]
    if not testid:
        names["pubsub"] = {ns: f"{survey}-{ns}-counter" for ns in name_stubs}
    else:
        names["pubsub"] = {ns: f"{survey}-{ns}-counter-{testid}" for ns in name_stubs}

    return names


def _log_and_print(msg, severity="INFO"):
    print(msg)
    logger.log_text(msg, severity=severity)


def run(
    survey: str, testid: Union[str, bool], timeout: int, testrun: bool,
):
    """Collect and store all metadata in the Pub/Sub counters."""
    collector = MetadataCollector(survey, testid, timeout, testrun)
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

    def __init__(
        self,
        survey: str,
        testid: Union[str, bool],
        timeout: int = 45,
        testrun: bool = False,
    ):
        """Initialize a MetadataCollector.

        Args:
            survey: Broker instance `survey` keyword. Used to label resources.
            testid: Broker instance `testid` keyword. Used to label resources.
            timeout: Number of seconds to wait between checks to determine whether
                     messages are still streaming in. If no new messages have arrived
                     since the previous check, the subscription is assumed to be empty
                     and the streaming pull connection is closed.
            testrun: If True, pull for a single timeout duration and nack all messages.
        """
        self.testrun = testrun
        self.timeout = timeout

        names = _resource_names(survey, testid)
        self.bq_table = names["bq_table"]
        self.bq_table_cols = names["bq_table_cols"]
        self.pubsub_names = names["pubsub"]

        self.metadata_dfs_dict = {}  # Dict[str, pd.DataFrame] as {topic stub: df}
        self.metadata_df = None  # pd.DataFrame, all subscriptions joined
        # index that will be used to join subscription dfs
        schema_map = schema_maps.load_schema_map(survey, testid)
        self.index = [schema_map["objectId"], schema_map["sourceId"]]

    def collect_and_store_all_metadata(self):
        """Entry point for the MetadataCollector."""
        # collect it
        self._collect_all_metadata()  # populate self.metadata_dfs_dict
        # reorganize it
        self._format_dfs_for_join_and_load()  # set index and column names
        self._join_metadata()  # populate self.metadata_df
        # store it
        self._load_metadata_to_bigquery()

    def _collect_all_metadata(self):
        # iterate subscriptions,
        # call SubscriptionMetadataCollector to pull the messages and extract metadata,
        # store the result in self.metadata_dfs_dict
        self.metadata_dfs_dict = {}

        for topic_stub, sub_name in self.pubsub_names.items():
            # generate a df of metadata from all messages in the subscription
            sub_collector = SubscriptionMetadataCollector(
                (topic_stub, sub_name),
                self._get_names_of_fields_to_collect(topic_stub),
                timeout=self.timeout,
                testrun=self.testrun,
            )
            sub_collector.pull_and_process_messages()

            # stash the subscription's metadata
            if sub_collector.metadata_df is not None:
                self.metadata_dfs_dict[topic_stub] = sub_collector.metadata_df

    def _get_names_of_fields_to_collect(self, topic_stub) -> List[str]:
        """Return a list of metadata fields to be collected from this stream.

        Includes fields which will be uploaded to BigQuery, and fields needed to join
        the data from different streams.

        Args:
            `topic_stub`: Pub/Sub topic name stub of the stream being processed.
        Returns:
            List of the names of metadata attributes to be collected.
            Some separation characters ("_", "-", and ".") in the returned list may not
            match the real metadata attribute names. This discrepancy must be handled
            later, at the time of collection.
        """
        # field name(s) that will serve as the index to join the dfs
        requested_fields = [i for i in self.index]

        # field names from this topic to be loaded to bigquery (minus self.index).
        # parse these from the existing bigquery column names.
        bqcols = [c for c in self.bq_table_cols if c not in self.index]
        tfields = [c.split("__")[0] for c in bqcols if c.split("__")[1] == topic_stub]
        # actual metadata field names may contain "." or "-",
        # but bigquery col names only allow "_", so tfields is not properly formatted.
        # this will have to be handled by the SubscriptionMetadataCollector
        requested_fields.extend(tfields)

        # extra fields needed to properly join the dfs in _add_ids_to_alerts_stream()
        if topic_stub == "alerts":
            requested_fields.append("message_id")
        if topic_stub == "alert_avros":
            requested_fields.append("file_origin_message_id")

        return requested_fields

    def _format_dfs_for_join_and_load(self):
        """Standardize index/names/types so data can be joined, loaded to BigQuery."""
        oid, sid = self.index
        # all subscriptions have the index columns except the alerts df... fix it
        self._add_ids_to_alerts_stream()

        for topic_stub, df in self.metadata_dfs_dict.items():
            # set the index with explicit types
            df = df.astype({oid: str, sid: str})
            df = df.set_index([oid, sid])

            # convert some types
            if topic_stub == "alerts":
                # convert the kafka timestamp to np.datetime64
                df["kafka.timestamp"] = pd.to_datetime(
                    df["kafka.timestamp"], unit="ms", utc=True
                )
            elif topic_stub == "alert_avros":
                # convert the eventTime (str, RFC 3339) to np.datetime64
                df["eventTime"] = pd.to_datetime(df["eventTime"])
                df["ra"] = df["ra"].astype(np.float64)
                df["dec"] = df["dec"].astype(np.float64)

            # attach topic name stub to column names, separated by double underscore
            df.rename(columns=lambda x: f"{x}__{topic_stub}", inplace=True)

            # format column names; BigQuery accepts only letters, numbers, underscores
            df.rename(columns=lambda x: x.replace("-", "_"), inplace=True)
            df.rename(columns=lambda x: x.replace(".", "_"), inplace=True)

            # store it
            self.metadata_dfs_dict[topic_stub] = df

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
        if "alerts" not in self.metadata_dfs_dict.keys():
            return

        # column names
        oid, sid = self.index
        msg_id_origin = "file_origin_message_id"
        msg_id = "message_id"

        # get all the ids from the alert_avros metadata
        df_avros = self.metadata_dfs_dict["alert_avros"].reset_index()
        df_avros[msg_id] = df_avros[msg_id_origin].astype(int)
        df_avros = df_avros.set_index(msg_id)
        df_avros = df_avros[[oid, sid]]  # drop the columns we don't need
        df_avros = df_avros[~df_avros.index.duplicated(keep="first")]  # drop duplicates

        # add the ids to the alerts metadata
        df_alerts = self.metadata_dfs_dict["alerts"].reset_index()
        df_alerts = df_alerts.astype({msg_id: int}).set_index(msg_id)
        df_alerts[oid] = df_avros[oid]
        df_alerts[sid] = df_avros[sid]

        # handle messages that were not matched to an oid and sid
        null_ids = df_alerts[df_alerts[[oid, sid]].isnull().any(axis=1)].index
        if len(null_ids) > 0:
            # fill in the oid, sid with "unknown-{pubsub message_id}"
            def unk(row):
                return f"unknown-{row.name}"

            df_alerts.loc[df_alerts[oid].isnull(), oid] = df_alerts.apply(unk, axis=1)
            df_alerts.loc[df_alerts[sid].isnull(), sid] = df_alerts.apply(unk, axis=1)

            # log some info
            _log_and_print(
                (
                    f"Cannot match {len(null_ids)} messages from the alerts stream "
                    f"to an {oid} and {sid}. "
                    f"Their Pub/Sub message ids are: {null_ids.tolist()}"
                ),
                severity="DEBUG",
            )

        # store the updated df
        self.metadata_dfs_dict["alerts"] = df_alerts.reset_index()

    def _join_metadata(self):
        # join the subscription dfs on index
        alerts = self.metadata_dfs_dict["alerts"]
        allothers = [df for t, df in self.metadata_dfs_dict.items() if t != "alerts"]
        self.metadata_df = alerts.join(allothers, how="outer")

    def _load_metadata_to_bigquery(self):
        # by default, conforms the dataframe to the table schema
        # i.e., converts dtypes and drops extra columns
        gcp_utils.load_dataframe_bigquery(
            self.bq_table, self.metadata_df, logger=logger
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
        self,
        pubsub_names: Tuple[str, str],
        requested_fields: Optional[List[str]] = None,
        timeout: int = 45,
        testrun: bool = False,
    ):
        """Initialize a SubscriptionMetadataCollector.

        Args:
            pubsub_names: Pub/Sub stream to be processed, in the format
                          (topic name stub, full subscription name).
            requested_fields: Metadata field names requested.
                              Actual collected fields may be a subset of this if some
                              requested fields are not present.
                              If None, collect all fields.
            timeout: Number of seconds to wait between checks to determine whether
                     messages are still streaming in. If no new messages have arrived
                     since the previous check, the subscription is assumed to be empty
                     and the streaming pull connection is closed.
                     For a testrun, a 2 second timeout works well.
            testrun: If True, pull for a single timeout duration and nack all messages.
        """
        self.topic_stub, self.subscription = pubsub_names
        self.requested_fields = requested_fields
        self.testrun = testrun
        self.timeout = timeout

        self.metadata_df = None  # pd.DataFrame
        self.metadata_dicts_list = []  # List[dict]

    def pull_and_process_messages(self):
        """Entry point for the SubscriptionMetadataCollector."""
        # collect the metadata
        self._pull_messages_and_extract_metadata()  # populate self.metadata_dicts_list

        # for debugging: write to file in case next step fails
        # self._stash_dicts_to_json_file()

        # cast to dataframe
        if len(self.metadata_dicts_list) > 0:
            self._package_metadata_into_df()  # populate self.metadata_df

    def _pull_messages_and_extract_metadata(self):
        _log_and_print(f"Processing {self.subscription}")

        # start pulling and processing messages in a background thread
        streaming_pull_future = gcp_utils.streamingPull_pubsub(
            self.subscription, self._extract_metadata, block=False
        )

        # close the connection when no msgs arrive within at least 1 timeout duration
        still_streaming = True
        n = len(self.metadata_dicts_list)
        while still_streaming:
            time.sleep(self.timeout)

            if self.testrun:
                still_streaming = False

            n_new = len(self.metadata_dicts_list)
            if (n_new - n) == 0:
                still_streaming = False
            else:
                n = n_new

        streaming_pull_future.cancel()  # Trigger the shutdown.
        streaming_pull_future.result()  # Block until the shutdown is complete.

        # log the total
        _log_and_print(
            f"\tpulled {len(self.metadata_dicts_list)} messages from "
            f"{self.subscription} and extracted metadata."
        )

    def _extract_metadata(self, message):
        # process a pubsub message and extract metadata

        # collect the custom metadata; e.g., DIA ids
        metadata = {**message.attributes}

        # collect other metadata
        metadata["message_id"] = message.message_id
        metadata["publish_time"] = message.publish_time

        # handle uniqueness of messages coming from the alert_avros bucket
        if "alert_avros-counter" in self.subscription:
            metadata = self._package_alert_avros_metadata(message.data, metadata)

        # store the requested fields in the list
        self.metadata_dicts_list.append(self._dont_collect_extra_fields(metadata))

        # for now, assume everything went fine... update this if problems arise
        if self.testrun:
            message.nack()
        else:
            message.ack()

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

    def _dont_collect_extra_fields(self, metadata):
        if self.requested_fields is None:
            # keep everything
            return metadata

        else:
            keep_keys = self._keep_field_names(self.requested_fields, metadata.keys())
            # keep message_id so we can drop duplicates later
            keep_keys = keep_keys + ["message_id"]

            metadata_to_keep = {k: v for k, v in metadata.items() if k in keep_keys}

            return metadata_to_keep

    def _stash_dicts_to_json_file(self):
        # for debugging
        fname = f"metadata/{self.subscription}.json"
        with open(fname, "w") as fout:
            json.dump(self.metadata_dicts_list, fout, allow_nan=True)

    def _package_metadata_into_df(self):
        # cast the collected metadata to a df
        df = pd.DataFrame(self.metadata_dicts_list)
        n = len(df)

        # messages can be published multiple times. we only care about the first one.
        df = df.sort_values("publish_time").drop_duplicates("message_id", keep="first")
        # log the number we dropped
        nnew = len(df)
        if n - nnew > 0:
            _log_and_print(
                f"Dropping {n-nnew} messages that are duplicates of previously "
                f"published messages in the subscription {self.subscription}."
            )

        # keep only the requested fields
        keepcols = self._keep_field_names(self.requested_fields, df.columns)
        self.metadata_df = df[keepcols]

    def _keep_field_names(self, keep_fields, field_names):
        # metadata field names may contain "." or "-",
        # but names in self.requested_fields are formatted as bigquery col names
        # which only contain "_", so we need to match them

        # return list of field_names with a match in keep_fields,
        # treating "_", "-", and "." as equivalent.
        names_map = {f: f.replace("-", "_").replace(".", "_") for f in field_names}
        keep = [c for c in field_names if names_map[c] in keep_fields]
        return keep


if __name__ == "__main__":  # noqa
    parser = argparse.ArgumentParser()
    # survey
    parser.add_argument(
        "--survey",
        default="ztf",
        help="Broker instance `survey` keyword. Used to label resources.\n",
    )
    # testid. use one of `--testid=<mytestid>` or `--production`
    parser.add_argument(
        "--testid",
        default="test",
        help="Broker instance `testid` keyword (str). Used to label resources.\n",
    )
    parser.add_argument(
        "--production",
        dest="testid",
        action="store_false",
        help="Sets `testid=False` (bool). Use for broker production instances.\n",
    )
    parser.add_argument(
        "--timeout",
        default=45,
        type=int,
        help="Number of seconds to wait for messages before closing the connection.",
    )
    parser.add_argument(
        "--testrun",
        default=False,
        type=bool,
        help="If True, pull for a single timeout duration and nack all messages.",
    )

    known_args, _ = parser.parse_known_args()

    run(known_args.survey, known_args.testid, known_args.timeout, known_args.testrun)
