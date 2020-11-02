#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Parses locally downloaded ZTF alerts. It is based heavily on the ZTF alerts
tutorial: https://goo.gl/TsyEjx
"""

import gzip
import io
from pathlib import Path
from typing import List, Union

import aplpy
import fastavro
import matplotlib.pyplot as plt
from astropy.io import fits
from matplotlib.pyplot import Figure

from broker.ztf_archive._utils import get_ztf_data_dir
from .download_data import get_local_alerts

_AVRO_DATA = Union[dict, bytes]


def _parse_alert_file(path: Union[Path, str], raw: bool = False) -> _AVRO_DATA:
    """Return the contents of an avro file published by ZTF

    Args:
        path: The file path to read
        raw: Optionally return the file data as bytes (Default: False)

    Returns:
        The file contents as a dictionary or bytes
    """

    with open(path, 'rb') as f:
        if raw:
            return f.read()

        else:
            return next(fastavro.reader(f))


def get_alert_data(alert_id: int, raw: bool = False) -> _AVRO_DATA:
    """Return the contents of an avro file published by ZTF

    Args:
        alert_id: Unique ZTF identifier for the alert packet
        raw: Optionally return the file data as bytes (Default: False)

    Returns:
        The file contents as a dictionary
    """

    # Search for avro file in subdirectories
    path = next(get_ztf_data_dir().glob(f'*/{alert_id}.avro'))
    try:
        return _parse_alert_file(path, raw)

    except FileNotFoundError:
        raise ValueError(
            f'Data for "{alert_id}" not locally available (at {path}).')


def iter_alerts(num_alerts: int = None, raw: bool = False) -> Union[_AVRO_DATA, List[_AVRO_DATA]]:
    """Iterate over all locally available alert data

    If ``num_alerts`` is not specified, yield individual alerts. Otherwise,
    yield a list of alerts with length ``num_alerts``.

    Args:
        num_alerts: Maximum number of alerts to yield at a time (optional)
        raw: Return file data as bytes

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


def plot_cutout(packet: dict, fig: Figure = None, subplot: tuple = (1, 1, 1)) -> Figure:
    """Plot a single cutout image from an alert packet

    Args:
        packet: A ZTF alert packet
        fig: An optional matplotlib figure to plot on
        subplot: Optional subplot indices to plot on

    Returns:
        A matplotlib figure
    """

    stamp = packet['cutoutScience']['stampData']
    with gzip.open(io.BytesIO(stamp)) as infile:
        with fits.open(io.BytesIO(infile.read())) as hdu_list:
            if fig is None:
                fig = plt.figure(figsize=(4, 4))

            sub_fig = aplpy.FITSFigure(hdu_list[0], figure=fig, subplot=subplot)
            sub_fig.show_grayscale(stretch='arcsinh')

    return fig


def plot_stamps(packet: dict) -> Figure:
    """Plot all three stamps contained in a ZTF alert packet

    Args:
        packet: A ZTF alert packet

    Returns:
        A matplotlib figure
    """

    fig = plt.figure(figsize=(12, 4))
    for i, cutout in enumerate(['Science', 'Template', 'Difference']):
        sub_fig = plot_cutout(packet, fig=fig, subplot=(1, 3, i + 1))
        sub_fig.suptitle(cutout)

    return fig
