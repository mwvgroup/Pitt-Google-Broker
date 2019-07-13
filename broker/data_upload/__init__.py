#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``data_upload`` module provides utilities for ingesting generic data
into GCP. Please refer to the official GCP documentation for up to date
information on the pricing models associated with various data upload services.
"""

from ._ingest_alerts import upload_to_bigquery, upload_to_bucket
