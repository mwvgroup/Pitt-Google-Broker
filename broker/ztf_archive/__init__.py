#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""The ``ztf_archive`` module downloads and provides access to ZTF alerts from
the 24hr ZTF alerts archive.
"""

from ._download_data import download_data_date
from ._download_data import download_recent_data
from ._download_data import get_number_local_alerts
from ._download_data import get_number_local_releases
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps
