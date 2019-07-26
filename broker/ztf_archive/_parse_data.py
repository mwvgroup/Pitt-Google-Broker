#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module parses locally downloaded ZTF alerts. It is based heavily on
the ZTF alerts tutorial: https://goo.gl/TsyEjx
"""

import gzip
import io

import aplpy
import fastavro
import matplotlib.pyplot as plt
from astropy.io import fits

from ..utils import get_ztf_data_dir
from ._download_data import get_local_alerts

ZTF_DATA_DIR = get_ztf_data_dir()


def _parse_alert_file(path, raw=False):
    """Return the contents of an avro file published by ZTF

    Args:
        path (str): The file path to read
        raw (bool): Optionally return the file data as bytes (Default: False)

    Returns:
        The file contents as a dictionary or bytes
    """

    with open(path, 'rb') as f:
        if raw:
            return f.read()

        else:
            return next(fastavro.reader(f))


def get_alert_data(alertid, raw=False):
    """Return the contents of an avro file published by ZTF

    Args:
        alertid (int): Unique ZTF identifier for the alert packet
        raw    (bool): Optionally return the file data as bytes (Default: False)

    Returns:
        The file contents as a dictionary
    """

    path = next(ZTF_DATA_DIR.glob(f'*/{alertid}.avro'))
    try:
        return _parse_alert_file(path, raw)

    except FileNotFoundError:
        raise ValueError(
            f'Data for "{alertid}" not locally available (at {path}).')


def iter_alerts(num_alerts=None, raw=False):
    """Iterate over all locally available alert data

    If ``num_alerts`` is not specified, yield individual alerts. Otherwise,
    yield a list of alerts with length ``num_alerts``.

    Args:
        num_alerts (int): Maximum number of alerts to yield at a time (optional)
        raw       (bool): Return file data as bytes (Default: False)

    Yields:
        A list of dictionaries or bytes representing ZTF alert data
    """

    err_msg = 'num_alerts argument must be an int >= 1'
    if num_alerts and num_alerts <= 0:
        raise ValueError(err_msg)

    # Return individual alerts
    if num_alerts is None:
        for alert_id in get_local_alerts():
            yield get_alert_data(alert_id, raw)

        return

    # Return alerts as list
    alerts_list = []
    for alert_id in get_local_alerts():
        alerts_list.append(get_alert_data(alert_id, raw))
        if len(alerts_list) >= num_alerts:
            yield alerts_list
            alerts_list = []

    if alerts_list:
        yield alerts_list


def _plot_cutout(packet, fig=None, subplot=None, **kwargs):
    """Plot a single cutout image from an alert packet

    Args:
        packet   (dict): A ZTF alert packet
        fig       (fig): An optional matplotlib figure to plot on
        subplot (tuple): Optional subplot indices to plot on
        Any other formatting arguments for aplpy.FITSFigure

    Returns:
        A matplotlib figure
    """

    stamp = packet['cutoutScience']['stampData']
    with gzip.open(io.BytesIO(stamp), 'rb') as f:
        with fits.open(io.BytesIO(f.read())) as hdul:
            if fig is None:
                fig = plt.figure(figsize=(4, 4))

            if subplot is None:
                subplot = (1, 1, 1)

            ffig = aplpy.FITSFigure(
                hdul[0], figure=fig, subplot=subplot, **kwargs)
            ffig.show_grayscale(stretch='arcsinh')

    return ffig


def plot_stamps(packet):
    """Plot all three stamps contained in a ZTF alert packet

    Args:
        packet (dict): A ZTF alert packet

    Returns:
        A matplotlib figure
    """

    fig = plt.figure(figsize=(12, 4))
    for i, cutout in enumerate(['Science', 'Template', 'Difference']):
        ffig = _plot_cutout(packet, fig=fig, subplot=(1, 3, i + 1))
        ffig.set_title(cutout)

    return fig
