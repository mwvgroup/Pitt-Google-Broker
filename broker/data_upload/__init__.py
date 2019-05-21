#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``data_upload`` module provides utilities for ingesting generic data
into GCP. Please refer to the official GCP documentation for up to date
information on the pricing models associated with various data upload services.
"""

from ._ingest_alerts import batch_ingest, stream_ingest, upload_bucket_file
