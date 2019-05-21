#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``alert_ingestion`` module ingests alert data from the ZTF Alert Archive
into a BigQuery backend.
"""

from ._ingest_alerts import batch_ingest, stream_ingest
from .gcp_setup import get_bq_schema, setup_gcp

