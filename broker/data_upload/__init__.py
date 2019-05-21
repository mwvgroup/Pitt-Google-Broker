#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``alert_ingestion`` module ingests alert data from the ZTF Alert Archive
into a BigQuery backend.
"""

from ._ingest_alerts import _batch_ingest_alerts, _stream_ingest_meta
