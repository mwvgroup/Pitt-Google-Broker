#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Tools to create plots and figures."""

from datetime import timedelta
from matplotlib import pyplot as plt
from matplotlib.dates import date2num
import numpy as np
import pandas as pd
from pathlib import Path
import scipy.stats as st
from typing import Optional, Union

from broker_utils import gcp_utils


project_id = 'ardent-cycling-243415'


class MetadataPlotter:
    """Creates figures from broker metadata for a single night."""

    def __init__(
        self,
        query: Optional[Union[str, dict]] = None,
        df: Optional[pd.DataFrame] = None,
        savefig_dir: Optional[str] = None,
    ):
        """Initialize a MetadataPlotter.

        Args:
            query: Either the full SQL query as a string, or a dict to create the query.
                   dict must have the following key, value pairs:
                    - 'survey': (str)
                    - 'testid': (str)
                    - 'date': (str) in the format yyyymmdd
                    - 'limit': (int) (optional)
                    - 'columns': (List[str]) (optional)
        """
        msg = "Either `query` or `df` must not be `None`."
        assert ((query is not None) or (df is not None)), msg

        self.query = query

        if df is None:
            self.sql_stmnt, self.df = self._load_df_from_query()
        else:
            self.df = df

        # column name of origin timestamp,
        # used to calculate processing times and plot the incoming alert rate
        self.t0 = 'kafka_timestamp__alerts'
        self.t0bins = {  # set in _get_rate_hist_bins(), if needed
            'per_min': None,
            'per_sec': None,
        }

        # plot colors for each stream
        self.colors = {
            'jd': 'tab:red',
            'alerts': 'tab:green',
            'BigQuery': 'tab:blue',
            'alert_avros': 'tab:cyan',
            'eventTime__alert_avros': 'teal',
            'alerts_pure': 'tab:olive',
            # 'exgalac_trans': 'tab:blue',
            # 'salt2': 'tab:orange',
            'exgalac_trans_cf': 'tab:pink',
            'SuperNNova': 'tab:purple',
        }

        # directory for plt.savefig(). if None, show instead of save
        self.savefig_dir = savefig_dir
        # create the directory if it doesn't exist
        if savefig_dir is not None:
            Path(savefig_dir).mkdir(parents=True, exist_ok=True)

    def _load_df_from_query(self):
        if type(self.query) == dict:
            sql_stmnt = self._create_sql_statement()
        else:
            sql_stmnt = self.query
        print(f'Loading df from BigQuery using SQL statement: \n{sql_stmnt}')
        df = gcp_utils.query_bigquery(sql_stmnt).to_dataframe()
        return (sql_stmnt, df)

    def _create_sql_statement(self):
        dataset = f"{self.query['survey']}_alerts"
        if self.query['testid'] not in [False, 'False']:
            dataset = f"{dataset}_{self.query['testid']}"
        table = 'metadata'
        kafka_topic = f"ztf_{self.query['date']}_programid1"
        self.query.setdefault(
            'columns',
            [
                # 'objectId', 'candid',
                'ra__alert_avros',
                'kafka_timestamp__alerts',
                'publish_time__alerts',
                'publish_time__BigQuery',
                'publish_time__alert_avros',
                'eventTime__alert_avros',
                'publish_time__alerts_pure',
                'publish_time__exgalac_trans_cf',
                'publish_time__SuperNNova',
            ]
        )
        sql_stmnt = (
            f"SELECT {', '.join(self.query['columns'])} "
            f"FROM `{project_id}.{dataset}.{table}` "
            f"WHERE kafka_topic__alerts='{kafka_topic}'"
            # f"LIMIT 100"
        )
        if 'limit' in self.query.keys():
            sql_stmnt = f"{sql_stmnt} LIMIT {self.query['limit']}"

        return sql_stmnt

    def plot_rate_hist(self, col, ax, bin_per='min'):
        """Plot histogram of timestamps, i.e. alert rates."""
        if col == 't0':
            col = self.t0
            ylabel = f'incoming rate (alerts/{bin_per})'
        else:
            col = f'publish_time__{col}'
            ylabel = f'processing rate (alerts/{bin_per})'

        # get/set the bins
        bins = self._get_rate_hist_bins(bin_per)
        # color
        color = 'tab:olive'

        # plot
        self.df.hist(col, ax=ax, bins=bins, color=color, alpha=0.5)

        ax.set_ylim(bottom=0)
        ax.grid(False)
        ax.set_ylabel(ylabel)
        ax.yaxis.label.set_color(color)
        ax.tick_params(axis='y', colors=color)

    def plot_proc_time(self, topic_stub, ax, clip_first=0, marg_ax={}):
        """Plot the time difference between the `topic_stub` and Kafka timestamps."""
        bin_rate_per = 'min'
        # set the field name for the topic_stub timestamp
        if topic_stub.split('__')[0] == 'eventTime':
            t1 = topic_stub
        else:
            t1 = f'publish_time__{topic_stub}'

        # get initial set of rows to be plotted
        start_time = self.df[self.t0].min() + timedelta(minutes=clip_first)
        d = self.df.loc[self.df[self.t0] >= start_time].dropna(subset=[t1])

        # calculate the processing times
        d['proc_time'] = pd.to_numeric(d[t1]-d[self.t0])*1e-9  # seconds
        if topic_stub == 'jd':
            d['proc_time'] = d['proc_time'].abs()

        # get max before sigma clip
        max = np.round(d['proc_time'].max(), 1)

        # do sigma clipping
        _, low, upp = st.sigmaclip(d['proc_time'])
        d = d.loc[(d['proc_time'] > low) & (d['proc_time'] < upp)]

        # calculate some stats
        mean = d['proc_time'].mean()
        median = np.round(d['proc_time'].median(), 3)
        # std = np.round(proc_time.std(), 1)
        conf95 = st.norm.interval(alpha=0.95, loc=mean, scale=st.sem(d['proc_time']))
        pm = np.round(mean - conf95[0], 3)
        mean = np.round(mean, 3)

        # set kwargs
        color = self.colors[topic_stub]
        label = f"{topic_stub} (median* {median}, mean* {mean}+-{pm}, max {max})"
        alpha = 0.15

        # plots
        x, y = d[t1], d['proc_time']
        # scatter
        ax.scatter(x, y, s=5, color=color, label=label, alpha=alpha)
        # ax.legend(loc=4)
        # marginal histograms
        if 'x' in marg_ax.keys():
            marg_ax['x'].hist(
                x, bins=self._get_rate_hist_bins(bin_rate_per), color=color
            )
            marg_ax['x'].tick_params(axis="x", labelbottom=False)  # no labels
            marg_ax['x'].set_ylabel(f'(per {bin_rate_per})')
        if 'y' in marg_ax.keys():
            marg_ax['y'].hist(y, bins=100, orientation='horizontal', color=color)
            marg_ax['y'].tick_params(axis="y", labelleft=False)  # no labels

        # set axis stuff
        ax.set_ylim(bottom=0)
        if topic_stub != 'jd':
            # lbl = 'publish time - ZTF timestamp (sec)'
            lbl = 'Pub/Sub timestamp - Kafka timestamp (sec)'
        else:
            lbl = 'ZTF timestamp - start of exposure (sec)'
        ax.set_ylabel(lbl)
        # ax.yaxis.label.set_color(color)
        # ax.tick_params(axis='y', colors=color)
        ax.set_xlabel('publish time')

    def plot_ra(self, ax, timestamp_col='t0'):
        """Plot RA."""
        if timestamp_col == 't0':
            x = self.df[self.t0]
        else:
            x = self.df[timestamp_col]
        ra = self.df['ra__alert_avros']

        color = 'tab:orange'
        kwargs = {
            'facecolors': color,
            'edgecolors': 'none',
            'alpha': 0.15,
            's': 5,
        }
        ax.scatter(x, ra, **kwargs)

        ax.set_ylabel('RA (deg)')
        ax.yaxis.label.set_color(color)
        ax.tick_params(axis='y', colors=color)

    def _get_rate_hist_bins(self, bin_per='min'):
        bins = self.t0bins[f'per_{bin_per}']

        # set the bins, if needed
        if bins is None:
            start = self.df[self.t0].min()
            end = self.df[self.t0].max()

            if bin_per == 'sec':
                one_sec = timedelta(minutes=1)
                night_delta = end.ceil(freq='S') - start.floor(freq='S')
                secs = []
                for i in range(night_delta.seconds+1):
                    secs.append(start.floor(freq='S') + (i)*one_sec)
                bins = date2num(secs)

            elif bin_per == 'min':
                one_min = timedelta(minutes=1)
                night_delta = end.ceil(freq='T') - start.floor(freq='T')
                mins = []
                for i in range(int(night_delta.seconds/60)+1):
                    mins.append(start.floor(freq='T') + (i)*one_min)
                bins = date2num(mins)

            # store the bins for next time
            self.t0bins[f'per_{bin_per}'] = bins

        return bins

    def _get_plot_kwargs(self, topic_stub, stream_type):
        if stream_type == 'filter':
            kwargs = {
                'facecolors': 'none',
                'edgecolors': self.colors[topic_stub],
                # 's': 10,
                'alpha': 0.75,
            }

        else:
            kwargs = {
                'facecolors': self.colors[topic_stub],
                'edgecolors': 'none',
                'alpha': 0.75,
            }

            if stream_type == 'alerts':
                kwargs['alpha'] = 0.5

        return kwargs

    def _save_or_show(self, fname_stub):
        if self.savefig_dir is not None:
            plt.gcf().set_size_inches(10, 6.0)
            plt.savefig(self._create_fig_save_path(fname_stub), dpi='figure')
        else:
            plt.show(block=False)

    def _create_fig_save_path(self, fname_stub):
        format = 'png'
        fname = f"{self.savefig_dir}/{fname_stub}"
        try:
            s, tid, dt = self.query['survey'], self.query['testid'], self.query['date']
            if tid in [False, 'False']:
                fname = f"{fname}-{s}-{dt}"
            else:
                fname = f"{fname}-{s}_{tid}-{dt}"
        except (TypeError, KeyError):
            pass
        return f"{fname}.{format}"
