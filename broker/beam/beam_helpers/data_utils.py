#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``data_utils` module handles parsing and formatting for ZTF alerts.


Module Documentation
--------------------
"""

import logging
import json
import fastavro as fa
from apache_beam import DoFn


class extractAlertDict(DoFn):
    def process(self, msg):
        from io import BytesIO
        from fastavro import reader

        # Extract the alert data from msg -> dict
        with BytesIO(msg) as fin:
            # print(type(fin))
            alertDicts = [r for r in reader(fin)]

        # candid = alertDicts[0]['candid']
        # logging.info(f'Extracted alert data dict for candid {candid}')
        # print(f'{alertDicts[0]}')
        return alertDicts


class stripCutouts(DoFn):
    """before stripping the cutouts, the upload to BQ failed with the following:
    UnicodeDecodeError:
        'utf-8 [while running 'WriteToBigQuery/WriteToBigQuery/_StreamToBigQuery/
        StreamInsertRows/ParDo(BigQueryWriteFn)-ptransform-133664']'
        codec can't decode byte 0x8b in position 1: invalid start byte
    See Dataflow job ztf-alert-data-ps-extract-bq
    started on December 7, 2020 at 1:51:44 PM GMT-5
    """
    def process(self, alertDict):
        cutouts = ['cutoutScience', 'cutoutTemplate', 'cutoutDifference']
        alertStripped = {k:v for k, v in alertDict.items() if k not in cutouts}
        return [alertStripped]


class formatDictForPubSub(DoFn):
    def process(self, alertDict):
        """Converts alert packet dictionaries to format suitable for WriteToPubSub().
        Currently returns a bytes object (includes msg data only).
        Can be updated to return a :class:`~PubsubMessage` object.
        In that case, change WriteToPubSub() kwarg 'with_attributes' to `True`.
        See https://beam.apache.org/releases/pydoc/2.26.0/apache_beam.io.external.gcp.pubsub.html?highlight=writetopubsub#apache_beam.io.external.gcp.pubsub.WriteToPubSub
        """
        # convert dict -> bytes
        return [json.dumps(alertDict).encode('utf-8')]
