#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module downloads and provides access to ZTF alerts from the 24hr ZTF
alerts archive.

Examples:
>>> # Download recent data from the ZTF archive.
>>> # Note: Daily releases can be as large as several Gb
>>> download_data()
>>>
>>> # Retrieve the number of daily releases that have been downloaded
>>> print(get_number_local_releases())
>>>
>>> # Retrieve the number of alerts that have been downloaded
>>> # from all combined daily releases.
>>> print(get_number_local_alerts())
>>>
>>> # Iterate through local alert data
>>> for alert in iter_alerts():
>>>     alert_id = alert['candid']
>>>     print(alert_id)
>>>     break
>>>
>>> # Get data for a specific alert id
>>> alert_data = get_alert_data(alert_id)
>>> print(alert_data)
>>>
>>> # Plot stamp images for alert data
>>> fig = plot_stamps(alert_data)
>>> plt.show()
"""

from ._download_data import download_data
from ._download_data import get_number_local_alerts
from ._download_data import get_number_local_releases
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps
