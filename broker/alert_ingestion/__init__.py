#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``alert_ingestion`` module connects to the ZTF Kafka stream and ingests
alerts into the project database.
"""

from ._ingest_alerts import batch_ingest_alerts, stream_ingest_alerts
