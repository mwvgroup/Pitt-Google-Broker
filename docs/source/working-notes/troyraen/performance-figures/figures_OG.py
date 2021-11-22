#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Tools to create plots and figures."""

from datetime import timedelta
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
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
        self.t0bins = {  # set in _plot_incoming_rate_hist(), if needed
            'per_min': None,
            'per_sec': None,
        }

        # plot colors for each stream
        self.colors = {
            'alerts': 'tab:green',
            'eventTime__alert_avros': 'tab:blue',
            'alert_avros': 'tab:orange',
            'alerts_pure': 'tab:olive',
            'exgalac_trans': 'tab:blue',
            'salt2': 'tab:orange',
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
        collist = [
            # 'objectId', 'candid',
            'kafka_timestamp__alerts', 'publish_time__alerts',
            'publish_time__alert_avros', 'eventTime__alert_avros',
            'publish_time__alerts_pure',
            'publish_time__exgalac_trans', 'publish_time__salt2',
            'publish_time__exgalac_trans_cf', 'publish_time__SuperNNova',
        ]
        sql_stmnt = (
            f"SELECT {', '.join(collist)} "
            f"FROM `{project_id}.{dataset}.{table}` "
            f"WHERE kafka_topic__alerts='{kafka_topic}'"
            # f"LIMIT 100"
        )
        if 'limit' in self.query.keys():
            sql_stmnt = f"{sql_stmnt} LIMIT {self.query['limit']}"

        return sql_stmnt

    def plot_all(self, clip_first=0):
        """Create all plots in this class."""
        self.plot_alerts(clip_first=clip_first)
        self.plot_avros(clip_first=clip_first)
        self.plot_dataflow(clip_first=clip_first)
        self.plot_cloud_fncs(clip_first=clip_first)
        self.plot_compare_methods(clip_first=clip_first)

    def plot_alerts(self, clip_first=0):
        """Plot processing time for alerts stream."""
        fig = plt.figure()
        ax = fig.gca()

        kwargs = self._set_plot_kwargs('alerts', 'alerts')

        self._plot_proc_time('alerts', ax, kwargs, clip_first)

        plt.legend(loc=1)

        self._plot_incoming_rate_hist(ax.twinx())

        plt.title('Processing Time: alerts stream')
        self._save_or_show('alerts')

    def plot_avros(self, clip_first=0):
        """Plot processing time for avro file storage and related stream."""
        stubs = ['eventTime__alert_avros', 'alert_avros']

        fig = plt.figure()
        ax = fig.gca()

        for i, topic_stub in enumerate(stubs):
            kwargs = self._set_plot_kwargs(topic_stub, 'other')
            kwargs['zorder'] = i
            self._plot_proc_time(topic_stub, ax, kwargs, clip_first)

        plt.legend(loc=1)

        self._plot_incoming_rate_hist(ax.twinx())

        plt.title('Processing Time: avro storage')
        self._save_or_show('avro_storage')

    def plot_cloud_fncs(self, clip_first=0):
        """Plot processing time for streams generated by Cloud Functions."""
        filter_stubs = ['exgalac_trans_cf', ]
        class_stubs = ['SuperNNova', ]

        fig = plt.figure()
        ax = fig.gca()

        for i, topic_stub in enumerate(filter_stubs + class_stubs):
            if topic_stub in filter_stubs:
                kwargs = self._set_plot_kwargs(topic_stub, 'filter')
            else:
                kwargs = self._set_plot_kwargs(topic_stub, 'classifier')
            kwargs['zorder'] = i

            self._plot_proc_time(topic_stub, ax, kwargs, clip_first)

        plt.legend(loc=1)

        self._plot_incoming_rate_hist(ax.twinx())

        plt.title('Processing Time: Cloud Function streams')
        self._save_or_show('cloud_fncs')

    def plot_dataflow(self, clip_first=0):
        """Plot processing time for Dataflow streams."""
        filter_stubs = ['alerts_pure', 'exgalac_trans']
        class_stubs = ['salt2', ]

        fig = plt.figure()
        ax = fig.gca()

        for i, topic_stub in enumerate(filter_stubs + class_stubs):
            if topic_stub in filter_stubs:
                kwargs = self._set_plot_kwargs(topic_stub, 'filter')
            else:
                kwargs = self._set_plot_kwargs(topic_stub, 'classifier')
            kwargs['zorder'] = i

            self._plot_proc_time(topic_stub, ax, kwargs, clip_first)

        plt.legend(loc=1)

        self._plot_incoming_rate_hist(ax.twinx())

        plt.title('Processing Time: Dataflow streams')
        self._save_or_show('dataflow')

    def plot_compare_methods(self, clip_first=0):
        """Plot processing time for Salt2 and SuperNNova and their trigger streams."""
        # filter_stubs = ['exgalac_trans', 'exgalac_trans_cf', ]
        filter_stubs = []
        class_stubs = ['salt2', 'SuperNNova', ]
        # pair streams for logical plot order
        # stubs = [i for sublist in zip(filter_stubs, class_stubs) for i in sublist]
        stubs = class_stubs

        fig = plt.figure()
        ax = fig.gca()

        # ['alerts_pure'] + 'tab:green',
        for i, topic_stub in enumerate(stubs):
            if topic_stub in filter_stubs:
                kwargs = self._set_plot_kwargs(topic_stub, 'filter')
            else:
                kwargs = self._set_plot_kwargs(topic_stub, 'classifier')
            kwargs['alpha'] = 0.75
            kwargs['zorder'] = i

            self._plot_proc_time(topic_stub, ax, kwargs, clip_first)

        plt.legend(loc=1)

        self._plot_incoming_rate_hist(ax.twinx())

        plt.title('Processing Time: Dataflow vs Cloud Fncs')
        self._save_or_show('dataflow_vs_cloud_fncs')

    def _set_plot_kwargs(self, topic_stub, stream_type):
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

    def _plot_incoming_rate_hist(self, ax, bin_per='min', compare_cols=[]):
        cols = [self.t0] + [f'publish_time__{c}' for c in compare_cols]
        # get/set the bins
        bins = self.t0bins[f'per_{bin_per}']
        if bins is None:
            night = self.df[self.t0].max() - self.df[self.t0].min()
            if bin_per == 'sec':
                bins = int(night.seconds)+1  # 1 bin per second of the night
            elif bin_per == 'min':
                bins = int(night.seconds/60)+1  # 1 bin per minute of the night

        # plot
        # self.df.hist(self.t0, color='k', alpha=0.25, ax=ax, bins=bins)
        self.df.hist(cols, alpha=0.25, ax=ax, bins=bins, stacked=True)

        ax.set_ylim(bottom=0)
        ax.grid(False)
        if len(compare_cols) == 0:
            ax.set_ylabel(f'ZTF alert rate (alerts/{bin_per})')
        else:
            ax.set_ylabel(f'Rates (alerts/{bin_per})')
            ax.legend(loc=1)

    def _plot_proc_time(self, topic_stub, ax, kwargs={}, clip_first=0):
        if topic_stub.split('__')[0] == 'eventTime':
            t1 = topic_stub
        else:
            t1 = f'publish_time__{topic_stub}'

        start_time = self.df[self.t0].min() + timedelta(minutes=clip_first)
        d = self.df.loc[self.df[self.t0] >= start_time].dropna(subset=[t1])
        proc_time = pd.to_numeric(d[t1]-d[self.t0])*1e-9  # seconds

        mean = np.round(proc_time.mean(), 1)
        std = np.round(proc_time.std(), 1)

        default_kwargs = {
            'label': f"{topic_stub} ({mean}+-{std})",
            's': 5,
            'marker': 'o',
            'alpha': 0.75,
        }
        for k, v in default_kwargs.items():
            kwargs.setdefault(k, v)

        ax.scatter(d[self.t0], proc_time, **kwargs)

        ax.set_ylim(bottom=0)
        ax.set_ylabel('publish time - ZTF timestamp (sec)')

    def _save_or_show(self, fname_stub):
        if self.savefig_dir is not None:
            plt.gcf().set_size_inches(10, 6.0)
            plt.savefig(self._create_fig_save_path(fname_stub), dpi='figure')
        else:
            plt.show(block=False)

    def _create_fig_save_path(self, fname_stub):
        format = 'pdf'
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
