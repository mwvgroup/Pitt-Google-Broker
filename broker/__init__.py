#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""A cloud-based, alert distribution service designed to provide near
real-time processing for alerts from the  Zwicky Transient Facility (ZTF) and
the Large Synoptic Survey Telescope (LSST).
"""

import os

if not os.getenv('GPB_OFFLINE', False):
    from google.cloud import logging as cloud_logging

    cloud_logging.Client().setup_logging()

__version__ = 'development'
