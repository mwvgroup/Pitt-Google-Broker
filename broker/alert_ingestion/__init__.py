#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module connects to the ZTF Kafka stream and ingests alerts into
the project database.
"""

from ._ingest_alerts import ingest_alerts
