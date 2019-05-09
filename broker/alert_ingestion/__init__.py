#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module connects to the ZTF Kafka stream and ingests alerts into
the project database.

Examples:
>>> from broker import alert_ingestion
>>>
>>> # To ingest alerts via the BigQuery streaming interface
>>> alert_ingestion.stream_ingest_alerts()
>>>
>>> # To ingest 15 alerts at a time through the streaming interface
>>> # (The default number of alerts is 10)
>>> alert_ingestion.stream_ingest_alerts(15)
>>>
>>> # The same principles apply for the batch upload interface
>>> alert_ingestion.batch_ingest_alerts(15)
"""

from ._ingest_alerts import batch_ingest_alerts, stream_ingest_alerts
