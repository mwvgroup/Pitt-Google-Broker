#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""A cloud-based, alert distribution service designed to provide near
real-time processing for alerts from the  Zwicky Transient Facility (ZTF) and
the Large Synoptic Survey Telescope (LSST).
"""

from google.cloud import logging as cloud_logging

from ._gcp_setup import setup_gcp

cloud_logging.Client().setup_logging()

__version__ = 'development'
