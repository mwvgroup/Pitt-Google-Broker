#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""A cloud-based, alert distribution service designed to provide near
real-time processing for alerts from the  Zwicky Transient Facility (ZTF) and
the Large Synoptic Survey Telescope (LSST).
"""

import os as _os
from warnings import warn as _warn

from . import alert_acquisition, data_upload, xmatch, ztf_archive
from ._gcp_setup import setup_gcp

if 'BROKER_PROJ_ID' not in _os.environ:
    _warn('GCP project id is not set in the current environment. Please see '
          'documentation for instructions on setting BROKER_PROJ_ID '
          'in your environment')

if 'GOOGLE_APPLICATION_CREDENTIALS' not in _os.environ:
    _warn('GCP credentials path is not set in the current environment. Please '
          'see documentation for instructions on setting'
          'GOOGLE_APPLICATION_CREDENTIALS in your environment')

__version__ = '0.1.1'
