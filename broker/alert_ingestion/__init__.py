#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``alert_ingestion`` module handles all logic related to the ingestion
of Kafka alerts into the Google Cloud Platform. This includes correcting
schema definitions for compliance with strict Avro standards, uploading the
alert data to Cloud Storage, and publishing PubSub status messages for the
ingested alerts.
"""

from .consume import GCSKafkaConsumer, DEFAULT_ZTF_CONFIG
