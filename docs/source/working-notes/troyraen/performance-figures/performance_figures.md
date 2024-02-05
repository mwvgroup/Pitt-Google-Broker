# docs/source/working-notes/troyraen/performance-figures/performance_figures.md

## figures exploration

1. query metadata table
2. cast to df
3. calc deltas
4. calc alert rate
5. plot

```python
from matplotlib import pyplot as plt
from datetime import timedelta
from broker_utils import gcp_utils

project_id = 'ardent-cycling-243415'
dataset = 'ztf_alerts'
table = 'metadata'
kafka_topic = 'ztf_20210829_programid1'
collist = [
    'objectId', 'candid',
    'kafka_timestamp__alerts', 'publish_time__alerts',
    'publish_time__alert_avros', 'eventTime__alert_avros',
    'publish_time__alerts_pure',
    'publish_time__exgalac_trans', 'publish_time__salt2',
    'publish_time__exgalac_trans_cf', 'publish_time__SuperNNova',
]
query = (
    f"SELECT {', '.join(collist)} "
    f"FROM `{project_id}.{dataset}.{table}` "
    f"WHERE kafka_topic__alerts='{kafka_topic}' "
    # f"AND publish_time__exgalac_trans_cf IS NOT NULL "
    # f"LIMIT 100"
)
query_job = gcp_utils.query_bigquery(query)
df = query_job.to_dataframe()
d = df.dropna(axis=1, how='all').dropna()

# df['delta_snn'] = df['publish_time__SuperNNova']-df['kafka_timestamp__alerts']
# df['delta_salt2'] = df['publish_time__salt2']-df['kafka_timestamp__alerts']
# df['delta_snn_sec'] = pd.to_numeric(df['delta_snn'])*1e-9  # number of seconds


colors = [
    'tab:blue', 'tab:pink', 'tab:orange', 'tab:purple',
    'tab:olive', 'tab:cyan',  'tab:brown', 'tab:green',
]


def plot_alerts(df, clip_first=2):
    fig = plt.figure()
    ax = fig.gca()

    kwargs = {'c': 'tab:green', 'alpha': 0.25}
    _plot_proc_time(df, 'alerts', ax, kwargs, clip_first)

    plt.legend(loc=0)

    _plot_incoming_rate(df, ax.twinx())

    plt.title('Processing Time: alerts stream')
    plt.show(block=False)

def plot_avros(df, clip_first=2):
    stubs = ['eventTime__alert_avros', 'alert_avros']
    colors = ['tab:blue', 'tab:orange']

    fig = plt.figure()
    ax = fig.gca()

    for i, topic_stub in enumerate(stubs):
        kwargs = {'c': colors[i], 'zorder': i}
        _plot_proc_time(df, topic_stub, ax, kwargs, clip_first)

    plt.legend(loc=0)

    _plot_incoming_rate(df, ax.twinx())

    plt.title('Processing Time: avro storage')
    plt.show(block=False)

def plot_compare_methods(df, clip_first=0):
    filter_stubs = ['exgalac_trans', 'exgalac_trans_cf', ]
    class_stubs = ['salt2', 'SuperNNova', ]
    colors = ['tab:green', 'tab:blue', 'tab:pink', 'tab:orange', 'tab:purple', ]

    fig = plt.figure()
    ax = fig.gca()

    for i, topic_stub in enumerate(['alerts_pure'] + filter_stubs + class_stubs):
        if topic_stub in filter_stubs:
            kwargs = {'facecolors': 'none', 'edgecolors': colors[i], 's': 10, 'alpha': 1}
        else:
            kwargs = {'c': colors[i]}

        _plot_proc_time(df, topic_stub, ax, kwargs, clip_first)

    plt.legend(loc=0)

    _plot_incoming_rate(df, ax.twinx())

    plt.title('Processing Time')
    plt.show(block=False)

def _plot_incoming_rate(df, ax):
    t0 = 'kafka_timestamp__alerts'
    night = df[t0].max() - df[t0].min()
    bins = int(night.seconds/60)+1  # 1 bin per minute of the night
    # bins = int(night.seconds)+1  # 1 bin per second of the night

    df.hist(t0, color='k', alpha=0.25, ax=ax, bins=bins)
    ax.set_ylim(bottom=0)
    ax.set_ylabel('ZTF alert rate (alerts/min)')

def _plot_proc_time(df, topic_stub, ax, kwargs={}, clip_first=0):
    t0 = 'kafka_timestamp__alerts'
    if topic_stub.split('__')[0] == 'eventTime':
        t1 = topic_stub
    else:
        t1 = f'publish_time__{topic_stub}'

    start_time = df[t0].min() + timedelta(minutes=clip_first)
    d = df.loc[df[t0]>=start_time].dropna(subset=[t1])
    proc_time = pd.to_numeric(d[t1]-d[t0])*1e-9  # seconds

    mean = np.round(proc_time.mean(),1)
    std = np.round(proc_time.std(),1)

    default_kwargs = {
        'label': f"{topic_stub} ({mean}+-{std})",
        's': 5,
        'marker': 'o',
        'alpha': 0.5,
    }
    for k, v in default_kwargs.items():
        kwargs.setdefault(k, v)

    ax.scatter(d[t0], proc_time, **kwargs)

    ax.set_ylim(bottom=0)
    ax.set_ylabel('publish time - ZTF timestamp (sec)')
```


## test figures.py

```python
import figures as figs

query = {
    'survey': 'ztf',
    'testid': False,
    'date': '20210830',
    # 'limit': 100,
}
savefig_dir = 'figures'
mplot = figs.MetadataPlotter(query=query, savefig_dir=savefig_dir)
mplot.plot_all(clip_first=2)
# mplot.plot_alerts(clip_first=0)
# mplot.plot_avros(clip_first=0)
# mplot.plot_dataflow(clip_first=0)
# mplot.plot_cloud_fncs(clip_first=0)
# mplot.plot_compare_methods(clip_first=0)

```
