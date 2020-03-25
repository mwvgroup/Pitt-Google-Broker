#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module provides tests for the Pitt-Google Broker code.

Before running these tests:
    1. The environment variables ``GOOGLE_CLOUD_PROJECT`` and
    ``GOOGLE_APPLICATION_CREDENTIALS`` must be set (see broker installation
    instructions).
    2. The dataset referenced by the ``dataset_id`` variable in the
    ``test_format_alerts`` module must exist
    and the user must have appropriate permissions (for details, see
    https://cloud.google.com/bigquery/docs/loading-data-local).
"""
