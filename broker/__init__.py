#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""A cloud-based, alert distribution service designed to provide near
real-time processing for alerts from the  Zwicky Transient Facility (ZTF) and
the Large Synoptic Survey Telescope (LSST).
"""

import os
from warnings import warn

if not os.getenv('GPB_OFFLINE', False):
    from google.cloud import logging as cloud_logging

    cloud_logging.Client().setup_logging()

for _var in ('BROKER_PROJ_ID', 'GOOGLE_APPLICATION_CREDENTIALS'):
    if _var not in os.environ:
        warn(
            f'Environmental variable ``{_var}`` not found. '
            f'Some package functionality may not be available.'
        )

__version__ = 'development'
