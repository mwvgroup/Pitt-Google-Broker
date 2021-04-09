#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``beam`` module facilitates connecting Apache Beam pipelines
to Pitt-Google Broker's BigQuery databases and Pub/Sub streams.
"""

import apache_beam as beam

from . import bigquery as pgbbq


class ExtractHistoryDf(beam.DoFn):
    def __init__(self, source='bigquery'):
        super().__init__()
        self.source = source

    def process(self, row):
        if self.source == 'bigquery':
            lcdf = pgbbq._format_history_row_to_df(row)
            return [lcdf]


class ExtractAlertDict(beam.DoFn):
    def process(self, msg):
        from io import BytesIO
        from fastavro import reader

        # Extract the alert data from msg -> [dict]
        with BytesIO(msg) as fin:
            alertDicts = [r for r in reader(fin)]  # contains 1 dict

        return alertDicts
