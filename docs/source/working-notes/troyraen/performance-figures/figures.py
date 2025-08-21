#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Tools to create plots and figures."""

from datetime import timedelta
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from pathlib import Path
import pylab as pl
import scipy.stats as st
from typing import Optional, Union

from broker_utils import gcp_utils


project_id = "ardent-cycling-243415"


class MetadataPlotter:
    """Creates figures from broker metadata for a single night."""

    # module names for each stream
    modules = {
        "alerts": "Consumer",
        "BigQuery": "BigQuery",
        "alert_avros": "Cloud Storage",
        # 'eventTime__alert_avros': 'publish_time__alerts',
        "alerts_pure": "Purity",
        "AllWISE": "AllWISE",
        # 'exgalac_trans': 'tab:blue',
        # 'salt2': 'tab:orange',
        "exgalac_trans_cf": "Extragalactic Transients",
        "SuperNNova": "SuperNNova",
    }

    # plot colors for each stream
    colors = {
        "jd": "tab:red",
        "alerts": "tab:green",
        "BigQuery": "tab:blue",
        "alert_avros": "tab:cyan",
        "eventTime__alert_avros": "teal",
        "alerts_pure": "tab:olive",
        "AllWISE": "tab:orange",
        # 'exgalac_trans': 'tab:blue',
        # 'salt2': 'tab:orange',
        "exgalac_trans_cf": "tab:pink",
        "SuperNNova": "tab:purple",
    }

    def __init__(
        self,
        query: Optional[Union[str, dict]] = None,
        df: Optional[pd.DataFrame] = None,
        savefig_dir: Optional[str] = None,
        savefig_format: Optional[str] = "png",
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
        assert (query is not None) or (df is not None), msg

        self.query = query

        if df is None:
            self.sql_stmnt, self.df = self._load_df_from_query()
        else:
            self.df = df
        # entries get duplicated. keep only the earliest of each publish time
        timecols = [c for c in self.query["columns"] if "time" in c]
        self.df = self.df.sort_values(timecols).drop_duplicates(
            subset=["candid"], keep="first"
        )

        self.savefig_format = savefig_format

        # column name of origin timestamp,
        # used to calculate processing times and plot the incoming alert rate
        self.t0 = "kafka_timestamp__alerts"
        self.t0bins = {  # set in _get_rate_hist_bins(), if needed
            "per_min": None,
            "per_sec": None,
        }

        # plot colors for each stream
        self.triggers = {
            "alerts": self.t0,
            "BigQuery": "publish_time__alerts",
            "alert_avros": "publish_time__alerts",
            "eventTime__alert_avros": "publish_time__alerts",
            "alerts_pure": "publish_time__alerts",
            "AllWISE": "publish_time__alerts",
            # 'exgalac_trans': 'tab:blue',
            # 'salt2': 'tab:orange',
            "exgalac_trans_cf": "publish_time__alerts",
            "SuperNNova": "publish_time__exgalac_trans_cf",
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
        print(f"Loading df from BigQuery using SQL statement: \n{sql_stmnt}")
        df = gcp_utils.query_bigquery(sql_stmnt).to_dataframe()
        return (sql_stmnt, df)

    def _create_sql_statement(self):
        dataset = f"{self.query['survey']}_alerts"
        if self.query["testid"] not in [False, "False"]:
            dataset = f"{dataset}_{self.query['testid']}"
        table = "metadata"
        kafka_topic = f"ztf_{self.query['date']}_programid1"
        self.query.setdefault(
            "columns",
            [
                # 'objectId', 'candid',
                "ra__alert_avros",
                "kafka_timestamp__alerts",
                "publish_time__alerts",
                "publish_time__BigQuery",
                "publish_time__alert_avros",
                "eventTime__alert_avros",
                "publish_time__alerts_pure",
                "publish_time__exgalac_trans_cf",
                "publish_time__SuperNNova",
            ],
        )
        sql_stmnt = (
            f"SELECT {', '.join(self.query['columns'])} "
            f"FROM `{project_id}.{dataset}.{table}` "
            f"WHERE kafka_topic__alerts='{kafka_topic}'"
            # f"LIMIT 100"
        )
        if "limit" in self.query.keys():
            sql_stmnt = f"{sql_stmnt} LIMIT {self.query['limit']}"

        return sql_stmnt

    def make_paper_plot(self, col, tref, clip_first=0):
        """Create performance figure for 2022 paper."""
        fig = plt.figure()
        gs = fig.add_gridspec(
            2,
            2,
            width_ratios=(7, 1.3),
            height_ratios=(2, 7),
            left=0.1,
            right=0.9,
            bottom=0.1,
            top=0.9,
            wspace=0.05,
            hspace=0.05,
        )

        ax = fig.add_subplot(gs[1, 0])
        marg_ax = {
            "x": fig.add_subplot(gs[0, 0], sharex=ax),
            "y": fig.add_subplot(gs[1, 1], sharey=ax),
            # 'dt': fig.add_subplot(gs[0, 1]),
        }
        dt, stats = self.plot_proc_time(
            col, ax, tref=tref, clip_first=clip_first, marg_ax=marg_ax
        )
        # fig.suptitle(title)
        if col == "alerts":
            ntot = len(self.df.dropna(subset=["publish_time__alerts"]))
            label = f"  {dt}\n{ntot:,} alerts"
            location = (1.03, 0.4)
        else:
            label = f"{dt}"
            location = (1.05, 0.6)
        marg_ax["x"].annotate(label, location, xycoords="axes fraction")
        fig.autofmt_xdate()
        self._save_or_show(f"{col}-{tref}")
        if self.savefig_dir is not None:
            plt.close(fig)

        return stats

    def plot_rate_hist(self, col, ax, bin_per="min"):
        """Plot histogram of timestamps, i.e. alert rates."""
        if col == "t0":
            col = self.t0
            ylabel = f"incoming rate (alerts/{bin_per})"
        else:
            col = f"publish_time__{col}"
            ylabel = f"processing rate (alerts/{bin_per})"

        # get/set the bins
        bins = self._get_rate_hist_bins(bin_per)
        # color
        color = "tab:olive"

        # plot
        self.df.hist(col, ax=ax, bins=bins, color=color, alpha=0.5)

        ax.set_ylim(bottom=0)
        ax.grid(False)
        ax.set_ylabel(ylabel)
        ax.yaxis.label.set_color(color)
        ax.tick_params(axis="y", colors=color)

    def plot_proc_time(self, topic_stub, ax, tref="Kafka", clip_first=0, marg_ax={}):
        """Plot the time difference between the `topic_stub` and Kafka timestamps."""
        # set the timestamp reference column
        if tref == "Kafka":
            t0 = self.t0
        elif tref == "Trigger":
            t0 = self.triggers[topic_stub]
        else:
            raise ValueError("`tref` must be one of `'Kafka'` or `'Trigger'`.")
        # set the field name for the topic_stub timestamp
        if topic_stub.split("__")[0] == "eventTime":
            t1 = topic_stub
        else:
            t1 = f"publish_time__{topic_stub}"

        # get initial set of rows to be plotted
        start_time = self.df[t0].min() + timedelta(minutes=clip_first)
        d = self.df.loc[self.df[t0] >= start_time].dropna(subset=[t1])

        # calculate the processing times
        d["proc_time"] = pd.to_numeric(d[t1] - d[t0]) * 1e-9  # seconds
        if topic_stub == "jd":
            d["proc_time"] = d["proc_time"].abs()

        # get max before sigma clip
        ptmax = d["proc_time"].max()

        # do sigma clipping
        _, low, upp = st.sigmaclip(d["proc_time"])
        d = d.loc[(d["proc_time"] > low) & (d["proc_time"] < upp)]

        # calculate some stats
        mean = d["proc_time"].mean()
        median = np.round(d["proc_time"].median(), 3)
        conf95 = st.norm.interval(alpha=0.95, loc=mean, scale=st.sem(d["proc_time"]))
        stats = {
            "total_alerts": len(d),
            "n_clipped": len(self.df.dropna(subset=[t1])) - len(d),
            "max": ptmax,
            "mean": mean,
            "median": median,
            "conf95": conf95,
            "pm": np.round(mean - conf95[0], 3),
            # "std": np.round(proc_time.std(), 1),
            "calculated after sigma clipping": [
                "total_alerts",
                "mean",
                "median",
                "conf95",
                "pm",
            ],
        }

        # set kwargs
        color = MetadataPlotter.colors[topic_stub]
        # label = (
        #     f"median* = {median:.3g} sec\n"
        #     f"  mean* = {mean:.3g}$\pm${pm:.3g} sec\n"
        #     f"    max = {ptmax:.3g} sec"
        # )
        # ax.annotate(
        #     label,
        #     (0.05, 0.05),
        #     xycoords="axes fraction",
        #     bbox=dict(facecolor='white', edgecolor='black', pad=5, lw=0.5)
        # )

        # plots
        xy = d.loc[d[t1].notnull(), [t1, "proc_time"]]
        x, y = xy[t1], xy["proc_time"]
        # scatter
        # ax.hexbin(pl.date2num(x), y)  # , color=color)
        # ax.xaxis_date()
        ax.scatter(x, y, s=5, color=color)
        ax.axhline(median, lw=1, color="k", label=f"{np.round(median, 3)} (sec) median")
        # ax.text(
        #     x.max(), median, f"{median}", backgroundcolor='w', ha="left", va="bottom"
        # )

        # ax.yaxis.set_ticks(np.sort(np.append(ax.get_yticks(), median)))
        # ax.legend()
        # marginal histograms
        if "x" in marg_ax.keys():
            n, _, _ = marg_ax["x"].hist(x, bins=self._bins_per_min(x), color=color)
            # marg_ax['x'].tick_params(which='both', length=7)
            # plt.plot()  # force set ax lims
            ymax = max(marg_ax["x"].get_yticks().max(), int(n.max() / 10) * 10)
            step = int(ymax / 4)
            yticks = np.arange(0, ymax + step, step)
            yticks = yticks[: np.where(yticks > n.max())[0][0] + 1]
            # yticks = yticks[:-1]
            marg_ax["x"].yaxis.set_ticks(yticks)
            marg_ax["x"].tick_params(axis="x", labelbottom=False)  # no labels
            marg_ax["x"].set_ylabel("N alerts\n(per min)")
        if "y" in marg_ax.keys():
            n, _, _ = marg_ax["y"].hist(
                y, bins=100, orientation="horizontal", color=color
            )
            marg_ax["y"].axhline(median, lw=1, color="k")
            marg_ax["y"].text(
                n.max(),
                median,
                f"{np.round(median, 3)}",
                rotation=310,
                ha="right",
                va="bottom",
            )
            marg_ax["y"].tick_params(axis="y", labelleft=False)  # no labels
            marg_ax["y"].set_xlabel("N alerts")

        # set axis stuff
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.set_ylim(bottom=0)
        if topic_stub != "jd":
            if tref == "Kafka" or topic_stub == "alerts":
                lbl = "Cumulative latency (sec)"
            elif tref == "Trigger":
                lbl = "Module processing time (sec)"
        else:
            lbl = "ZTF timestamp - start of exposure (sec)"
        ax.set_ylabel(lbl)
        # ax.yaxis.label.set_color(color)
        # ax.tick_params(axis='y', colors=color)
        ax.set_xlabel("Pub/Sub publish time (UTC)")

        # get the date
        dt = list(set(x.apply(lambda i: i.strftime("%Y-%m-%d"))))
        assert len(dt) == 1  # make sure only one day is being plotted
        return (dt[0], stats)

    def plot_ra(self, ax, timestamp_col="t0"):
        """Plot RA."""
        if timestamp_col == "t0":
            x = self.df[self.t0]
        else:
            x = self.df[timestamp_col]
        ra = self.df["ra__alert_avros"]

        color = "tab:orange"
        kwargs = {
            "facecolors": color,
            "edgecolors": "none",
            "alpha": 0.15,
            "s": 5,
        }
        ax.scatter(x, ra, **kwargs)

        ax.set_ylabel("RA (deg)")
        ax.yaxis.label.set_color(color)
        ax.tick_params(axis="y", colors=color)

    def _bins_per_min(self, dtime):
        one_min = timedelta(minutes=1)
        start = dtime.min()
        end = dtime.max()
        night_delta = end.ceil(freq="T") - start.floor(freq="T")
        mins = []
        for i in range(int(night_delta.seconds / 60) + 1):
            mins.append(start.floor(freq="T") + (i) * one_min)
        bins = mdates.date2num(mins)
        return bins

    def _get_rate_hist_bins(self, bin_per="min"):
        bins = self.t0bins[f"per_{bin_per}"]

        # set the bins, if needed
        if bins is None:
            start = self.df[self.t0].min()
            end = self.df[self.t0].max()

            if bin_per == "sec":
                one_sec = timedelta(minutes=1)
                night_delta = end.ceil(freq="S") - start.floor(freq="S")
                secs = []
                for i in range(night_delta.seconds + 1):
                    secs.append(start.floor(freq="S") + (i) * one_sec)
                bins = mdates.date2num(secs)

            elif bin_per == "min":
                one_min = timedelta(minutes=1)
                night_delta = end.ceil(freq="T") - start.floor(freq="T")
                mins = []
                for i in range(int(night_delta.seconds / 60) + 1):
                    mins.append(start.floor(freq="T") + (i) * one_min)
                bins = mdates.date2num(mins)

            # store the bins for next time
            self.t0bins[f"per_{bin_per}"] = bins

        return bins

    def _get_plot_kwargs(self, topic_stub, stream_type):
        if stream_type == "filter":
            kwargs = {
                "facecolors": "none",
                "edgecolors": MetadataPlotter.colors[topic_stub],
                # 's': 10,
                "alpha": 0.75,
            }

        else:
            kwargs = {
                "facecolors": MetadataPlotter.colors[topic_stub],
                "edgecolors": "none",
                "alpha": 0.75,
            }

            if stream_type == "alerts":
                kwargs["alpha"] = 0.5

        return kwargs

    def _save_or_show(self, fname_stub):
        if self.savefig_dir is not None:
            plt.gcf().set_size_inches(10, 4.5)
            dpi = 300 if self.savefig_format == "png" else "figure"
            plt.savefig(
                self._create_fig_save_path(fname_stub),
                dpi=dpi,
                bbox_inches="tight",
                format=self.savefig_format,
            )
        else:
            plt.show(block=False)

    def _create_fig_save_path(self, fname_stub):
        format = self.savefig_format
        if fname_stub.split("-")[0] == "alert_avros":
            fstub = "-".join(["avros"] + fname_stub.split("-")[1:])
        else:
            fstub = fname_stub
        fname = f"{self.savefig_dir}/{fstub}"
        try:
            s, tid, dt = self.query["survey"], self.query["testid"], self.query["date"]
            if tid in [False, "False"]:
                fname = f"{fname}-{s}-{dt}"
            else:
                fname = f"{fname}-{s}_{tid}-{dt}"
        except (TypeError, KeyError):
            pass
        return f"{fname}.{format}"
