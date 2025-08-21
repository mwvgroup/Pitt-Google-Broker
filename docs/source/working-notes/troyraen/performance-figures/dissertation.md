# docs/source/working-notes/troyraen/performance-figures/dissertation.md

## Performance figures for disseration

Setup

```python
from collections import namedtuple
from matplotlib import pyplot as plt
import pandas as pd
import pprint

from broker_utils import gcp_utils

import figures as figs


plt.rcParams.update(
    {
        "text.usetex": True,
        "mathtext.fontset": "cm",
        "font.family": "STIXGeneral",
        "font.size": 15,
    }
)
```

Query for number of nightly ZTF alerts.

```python
query = """
    SELECT
      kafka_topic__alerts, COUNT(DISTINCT candid) as num_alerts
    FROM
      `ardent-cycling-243415.ztf_alerts.metadata`
    GROUP BY kafka_topic__alerts
"""

daily_counts_df = gcp_utils.query_bigquery(query).to_dataframe()
daily_counts_df.to_csv("daily_counts.dat")
```

Query for processing times and make plots.

```python
# load dataframes into a MetadataPlotter object
def load_plotter(qdate, read_csv=True, save_csv=False, loaddf=None):
    # set all the options
    survey, testid = "ztf", False
    savefig_format = "png"
    querycols = [
        "candid",
        "kafka_timestamp__alerts",
        "publish_time__alerts",
        "publish_time__BigQuery",
        "publish_time__alert_avros",
        # 'publish_time__AllWISE',
        # 'publish_time__alerts_pure',
        "publish_time__exgalac_trans_cf",
        "publish_time__SuperNNova",
    ]
    savefig_dir = f"figures/{qdate}"
    data_file = f"{savefig_dir}/{qdate}.dat"
    kwargs = {
        "query": {
            "survey": survey,
            "testid": testid,
            "date": qdate,
            "columns": querycols,
        },
        "savefig_dir": savefig_dir,
        "savefig_format": savefig_format,
    }
    # specify where to get the dataframe from
    if loaddf:
        print("Loading from the supplied df")
        kwargs["df"] = loaddf.df
    elif read_csv:
        print("Loading from file")
        kwargs["df"] = pd.read_csv(
            data_file,
            parse_dates=[i for i in querycols if "time" in i],
            infer_datetime_format=True,
        )
    else:
        print("Querying BigQuery")

    mplots = figs.MetadataPlotter(**kwargs)

    if save_csv:
        mplots.df.to_csv(data_file, index=False)

    return mplots


mplots = {}
for qdate in ["20220401", "20220429"]:  # , "20220404", "20210927"]
    k = str(int(qdate[-4:]))  # use mmdd as the key, drop leading zeros
    mplots[k] = load_plotter(qdate, loaddf=mplots.get(k, None))

# make figures
plotcols = ["alerts", "BigQuery", "alert_avros", "SuperNNova"]
clip_first = 0
for k, mp in mplots.items():
    for c in plotcols:
        for tref in ["Trigger"]:  # , 'Kafka']:
            print(f"Making {c} plot for {mp.query['date']}, tref={tref}")
            stats = mp.make_paper_plot(c, tref)
            pprint.pprint(stats)
            print()


# mplot = figs.MetadataPlotter(df=mplot.df, query=query, savefig_dir=savefig_dir, savefig_format=savefig_format)


# plot processing times with marginal histograms
```
