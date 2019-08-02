#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""The ``ztf_archive`` module downloads and provides access to ZTF alerts from
the ZTF Public Alerts Archive.
"""

import os as _os
from warnings import warn as _warn

from ._download_data import ZTF_URL as archive_url
from ._download_data import create_ztf_sync_table
from ._download_data import delete_local_data
from ._download_data import download_data_date
from ._download_data import download_recent_data
from ._download_data import get_local_alerts
from ._download_data import get_local_releases
from ._download_data import get_remote_md5_table
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps

if 'PGB_DATA_DIR' not in _os.environ:
    _warn('ZTF data directory not set in the current environment. Please '
          'see documentation for instructions on setting'
          'PGB_DATA_DIR in your environment')
