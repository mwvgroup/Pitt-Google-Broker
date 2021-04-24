#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``data_utils` module handles parsing and formatting for alerts.


Module Documentation
--------------------
"""

from apache_beam import DoFn
import logging
import fastavro as fa
import json
import numpy as np

# map PGB generic names to survey schema names
schema_maps = {  # pgb_field_name: survey_field_name
    'ztf': {
        'objectId':         'objectId',
        'source':           'candidate',
        'sourceId':         'candid',
        'prvSources':       'prv_candidates',
        'cutoutScience':    'cutoutScience',
        'cutoutTemplate':   'cutoutTemplate',
        'cutoutDifference': 'cutoutDifference',
    },
    'decat': {
        'objectId':         'objectid',
        'source':           'triggersource',
        'sourceId':         'sourceid',
        'prvSources':       'sources',
        'cutoutScience':    'scicutout',
        'cutoutTemplate':   'refcutout',
        'cutoutDifference': 'diffcutout',
    }
}


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


class extractDIASource(DoFn):
    """Extract the DIA source` fields and information needed for provinance
    from the alertDict.
    """
    def process(self, alertDict):
        SURVEY = self.guess_survey(alertDict)

        if SURVEY == 'ztf':
            source = self.process_ztf(alertDict)
        elif SURVEY == 'decat':
            source = self.process_decat(alertDict)

        return source

    def process_decat(self, alertDict):
        # get source
        dup_cols = ['ra','dec']  # names duplicated in object and source levels
        sourcename = lambda x: x if x not in dup_cols else f'source_{x}'
        src = {sourcename(k):v for k,v in alertDict['triggersource']}

        # get info for provinance
        notmetakeys = ['triggersource', 'sources']
        metadict = {k:v for k,v in alertDict.items() if k not in notmetakeys}

        # get string of previous sources' sourceid, comma-separated
        if alertDict['sources'] is not None:
            tmp = [ps['sourceid'] for ps in alertDict['sources']]
            prv_sources = ','.join([f'{sid}' for sid in tmp if sid is not None])
        else:
            prv_sources = None

        # package it up and return
        source = {**metadict, **src, 'sources_sourceids': prv_sources}
        return [source]

    def process_ztf(self, alertDict):
        # get candidate
        cand = alertDict['candidate']
        del cand['candid']  # candid is repeated, drop the one nested here

        # get info for provinance
        metakeys = ['schemavsn', 'publisher', 'objectId', 'candid']
        metadict = {k:v for k,v in alertDict.items() if k in metakeys}

        # get string of previous candidates' candid, comma-separated
        if alertDict['prv_candidates'] is not None:
            tmp = [pc['candid'] for pc in alertDict['prv_candidates']]
            prv_candids = ','.join([f'{cid}' for cid in tmp if cid is not None])
        else:
            prv_candids = None

        # package it up and return
        candidate = {**metadict, **cand, 'prv_candidates_candids': prv_candids}
        return [candidate]

    def guess_survey(self, alertDict):
        # figure out which survey this is
        if schema_maps['ztf']['source'] in alertDict.keys():
            SURVEY = 'ztf'
        elif schema_maps['decat']['source'] in alertDict.keys():
            SURVEY = 'decat'
        else:
            raise ValueError('Cannot guess survey from alert packet.')
        return SURVEY

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
        SURVEY = self.guess_survey(alertDict)
        schema_map = schema_maps[SURVEY]

        cutouts = [
            schema_map['cutoutScience'],
            schema_map['cutoutTemplate'],
            schema_map['cutoutDifference']
        ]
        alertStripped = {k:v for k, v in alertDict.items() if k not in cutouts}

        return [alertStripped]

    def guess_survey(self, alertDict):
        # figure out which survey this is
        if schema_maps['ztf']['source'] in alertDict.keys():
            SURVEY = 'ztf'
        elif schema_maps['decat']['source'] in alertDict.keys():
            SURVEY = 'decat'
        else:
            raise ValueError('Cannot guess survey from alert packet.')
        return SURVEY


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
