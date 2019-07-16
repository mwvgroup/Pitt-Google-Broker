#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""The ``ztf_archive`` module downloads and provides access to ZTF alerts from
the ZTF Public Alerts Archive.
"""

import os as _os

from ._download_data import delete_local_data
from ._download_data import download_data_date
from ._download_data import download_recent_data
from ._download_data import get_local_alert_list
from ._download_data import get_local_release_list
from ._download_data import get_remote_release_list
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps

if 'PGB_DATA_DIR' not in _os.environ:
    raise RuntimeError("Variable 'PGB_DATA_DIR' not specified in environment")
