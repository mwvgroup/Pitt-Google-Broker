#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``figures`` contains functions for plotting alert and history data.
"""

import aplpy
from astropy.io import fits
from astropy.time import Time
import gzip
import io
import matplotlib as mpl
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from typing import Optional

from . import utils as pgbu


#--- Plot object history
def plot_lightcurve(dflc: pd.DataFrame,
                    objectId: Optional[str] = None,
                    ax: Optional[mpl.axes.Axes] = None,
                    days_ago: bool = True,
                    ):
    """Plot the lighcurve (per band) of a single ZTF object.
    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb

    Args:
        dflc: Lightcurve history of a unique objectId. Must contain columns
              ['jd','fid','magpsf','sigmapsf','diffmaglim']
        objectId: objectId identifying dflc. Used for plot title.
        ax: matplotlib axes for the figure. If None, a new figure will be created
        days_ago: If True, x-axis will be number of days in the past.
                  Else x-axis will be Julian date.
    """

    filter_code = pgbu.ztf_fid_names()  # dict
    filter_color = {1:'green', 2:'red', 3:'pink'}

    # set the x-axis (time) details
    if days_ago:
        now = Time.now().jd
        t = dflc.jd - now
        xlabel = 'Days Ago'
    else:
        t = dflc.jd
        xlabel = 'Time (JD)'

    if ax is None:
        plt.figure()

    # plot lightcurves by band
    for fid, color in filter_color.items():
        # plot detections in this filter:
        w = (dflc.fid == fid) & ~dflc.magpsf.isnull()
        if np.sum(w):
            label = f'{fid}: {filter_code[fid]}'
            kwargs = {'fmt':'.', 'color':color, 'label':label}
            plt.errorbar(t[w],dflc.loc[w,'magpsf'], dflc.loc[w,'sigmapsf'], **kwargs)
        # plot nondetections in this filter
        wnodet = (dflc.fid == fid) & dflc.magpsf.isnull()
        if np.sum(wnodet):
            plt.scatter(t[wnodet],dflc.loc[wnodet,'diffmaglim'], marker='v',color=color,alpha=0.25)

    plt.gca().invert_yaxis()
    plt.xlabel(xlabel)
    plt.ylabel('Magnitude')
    plt.legend()
    plt.title(f'objectId: {objectId}')


#--- Plot cutouts
def plot_stamp(stamp, fig=None, subplot=None, **kwargs):
    """Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    with gzip.open(io.BytesIO(stamp), 'rb') as f:
        with fits.open(io.BytesIO(f.read())) as hdul:
            if fig is None:
                fig = plt.figure(figsize=(4,4))
            if subplot is None:
                subplot = (1,1,1)
            ffig = aplpy.FITSFigure(hdul[0],figure=fig, subplot=subplot, **kwargs)
            ffig.show_grayscale(stretch='arcsinh')
            # This has been throwing: `ValueError: a must be > 0 and <= 1`
            # I think I have fixed this by requiring
            # astropy==3.2.1
            # astropy-healpix==0.6
            # beautifulsoup4==4.8
            # Note: I see this related thing: https://github.com/aplpy/aplpy/issues/420
            # but I am using the latest version (2.0.3).
            # ffig.show_grayscale()
    return ffig

def plot_cutouts(alert_dict):
    """Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    #fig, axes = plt.subplots(1,3, figsize=(12,4))
    fig = plt.figure(figsize=(12,4))
    for i, cutout in enumerate(['Science','Template','Difference']):
        stamp = alert_dict['cutout{}'.format(cutout)]['stampData']
        ffig = plot_stamp(stamp, fig=fig, subplot = (1,3,i+1))
        ffig.set_title(cutout)


#--- Plot all
def plot_lightcurve_cutouts(alert_dict):
    """Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    fig = plt.figure(figsize=(16,4))
    dflc = pgbu.alert_dict_to_dataframe(alert_dict)
    plot_lightcurve(dflc,ax = plt.subplot(1,4,1))
    for i, cutout in enumerate(['Science','Template','Difference']):
        stamp = alert_dict['cutout{}'.format(cutout)]['stampData']
        ffig = plot_stamp(stamp, fig=fig, subplot = (1,4,i+2))
        ffig.set_title(cutout)
