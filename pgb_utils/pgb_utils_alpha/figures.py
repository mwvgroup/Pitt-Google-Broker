#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``bigquery`` contains functions that facilitate querying
Pitt-Google Broker's BigQuery databases and reading the results.
"""

from astropy.time import Time
import matplotlib as mpl
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from typing import Optional


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

    filter_code = {1:'g', 2:'R', 3:'i'}
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
