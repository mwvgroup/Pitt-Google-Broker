#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``beam_transforms`` module contains common functions used by the broker in
Apache Beam jobs.
"""

from apache_beam import DoFn


class ExtractAlertDict(DoFn):
    """Extract the alert packet from a Pub/Sub message (bytes object) and
    return it as a dictionary.
    """
    def process(self, msg):
        from io import BytesIO
        from fastavro import reader

        with BytesIO(msg) as fin:
            alertDicts = [r for r in reader(fin)]
            # list of dicts, generally expected to have length 1
        return alertDicts


class StripCutouts(DoFn):
    """Drop the cutouts from the alert dictionary.
    """
    def __init__(self, schema_map):
        super().__init__()
        self.schema_map = schema_map

    def process(self, alertDict):
        import copy

        schema_map = self.schema_map
        cutouts = [
            schema_map['cutoutScience'],
            schema_map['cutoutTemplate'],
            schema_map['cutoutDifference']
        ]

        if schema_map['SURVEY'] == 'decat':
            alertStripped = copy.deepcopy(alertDict)
            for co in cutouts:
                alertStripped[schema_map['source']].pop(co, None)
                for psource in alertStripped[schema_map['prvSources']]:
                    psource.pop(co, None)

        elif schema_map['SURVEY'] == 'ztf':
            alertStripped = {k:v for k, v in alertDict.items() if k not in cutouts}

        return [alertStripped]


class ExtractDIASource(DoFn):
    """Extract the DIA source` fields and information needed for provenance
    from the alertDict.
    """
    def __init__(self, schema_map):
        super().__init__()
        self.schema_map = schema_map

    def process(self, alertDict):
        SURVEY = self.schema_map['SURVEY']
        if SURVEY == 'ztf':
            source = self.process_ztf(alertDict)
        elif SURVEY == 'decat':
            source = self.process_decat(alertDict)

        return source

    def process_decat(self, alertDict):
        # get source
        dup_cols = ['ra','dec']  # names duplicated in object and source levels
        sourcename = lambda x: x if x not in dup_cols else f'source_{x}'
        src = {sourcename(k):v for k,v in alertDict['triggersource'].items()}

        # get info for provenance
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
        dup_cols = ['candid']  # candid is repeated, drop the one nested here
        cand = {k:v for k,v in alertDict['candidate'].items() if k not in dup_cols}

        # get info for provenance
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

class FormatDictForPubSub(DoFn):
    def process(self, alertDict):
        """Converts alert packet dictionaries to format suitable for WriteToPubSub().
        Currently returns a bytes object (includes msg data only).
        Can be updated to return a :class:`~PubsubMessage` object.
        In that case, change WriteToPubSub() kwarg 'with_attributes' to `True`.
        See https://beam.apache.org/releases/pydoc/2.26.0/apache_beam.io.external.gcp.pubsub.html?highlight=writetopubsub#apache_beam.io.external.gcp.pubsub.WriteToPubSub
        """
        import json
        # convert dict -> bytes
        return [json.dumps(alertDict).encode('utf-8')]
