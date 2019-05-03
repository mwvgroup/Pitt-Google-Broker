#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module connects to the ZTF Kafka stream and ingests alerts into
the project database.

Examples:
>>> from google.cloud import bigquery
>>>
>>> client = bigquey.Client()
>>>
>>> # To ingest alerts via the BigQuery streaming interface
>>> stream_ingest_alerts(client)
>>>
>>> # To ingest 15 alerts at a time through the streaming interface
>>> # (The default number of alerts is 10)
>>> stream_ingest_alerts(client, 15)
>>>
>>> # The same principles apply for the batch upload interface
>>> batch_ingest_alerts(15)
"""

from ._ingest_alerts import batch_ingest_alerts, stream_ingest_alerts
