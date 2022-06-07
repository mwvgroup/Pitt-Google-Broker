# performance-figures: test figures.py

```python
from matplotlib import pyplot as plt
import figures as figsk

query = {
    'survey': 'ztf',
    'testid': False,
    'date': '20210927',
    # 'limit': 100,
    'columns': [
                    'kafka_timestamp__alerts',
                    'publish_time__alerts',
                    'publish_time__BigQuery',
                    'publish_time__alert_avros',
                    'publish_time__AllWISE',
                    # 'publish_time__alerts_pure',
                    'publish_time__exgalac_trans_cf',
                    'publish_time__SuperNNova',
                ]
}
savefig_dir = 'figures/20210927'
mplot = figs.MetadataPlotter(query=query, savefig_dir=savefig_dir)
# mplot = figs.MetadataPlotter(df=mplot.df, query=query, savefig_dir=savefig_dir)

# plot processing times with marginal histograms
cols = ['alerts', 'BigQuery', 'alert_avros', 'AllWISE', 'exgalac_trans_cf', 'SuperNNova']
clip_first = 0
for c in cols:
    for tref in ['Kafka', 'Trigger']:
        plot_proct()

def plot_proct():
    fig = plt.figure()
    gs = fig.add_gridspec(2, 2,  width_ratios=(7, 1.3), height_ratios=(2, 7),
                          left=0.1, right=0.9, bottom=0.1, top=0.9,
                          wspace=0.05, hspace=0.05)

    ax = fig.add_subplot(gs[1, 0])
    marg_ax = {
        'x': fig.add_subplot(gs[0, 0], sharex=ax),
        'y': fig.add_subplot(gs[1, 1], sharey=ax),
    }
    mplot.plot_proc_time(c, ax, tref=tref, clip_first=clip_first, marg_ax=marg_ax)
    fig.autofmt_xdate()
    if tref == 'Kafka':
        title = f"{c.split('__')[-1]} - processing time: cumulative"
    elif tref == 'Trigger':
        title = f"{c.split('__')[-1]} - processing time: single component"
    fig.suptitle(title)
    mplot._save_or_show(f'{c}-{tref}')
    if mplot.savefig_dir is not None:
        plt.close(fig)

# t0 and RA
fig = plt.figure()
ax = plt.gca()
mplot.plot_ra(ax, timestamp_col='t0')
mplot.plot_rate_hist('t0', ax.twinx())
fig.autofmt_xdate()
# plt.show(block=False)
plt.title('Incoming Alerts (ZTF, Kafka)')
mplot._save_or_show('ztf')

# processing times and rate hists
cols = ['alerts', 'BigQuery', 'alert_avros', 'exgalac_trans_cf', 'SuperNNova']
clip_first = 2
for c in cols:
    fig = plt.figure()
    ax = plt.gca()
    mplot.plot_proc_time(c, ax, clip_first=clip_first)
    plt.legend(loc=1)
    mplot.plot_rate_hist(c, ax.twinx())
    fig.autofmt_xdate()
    # plt.show(block=False)
    plt.title(f'{c} (Pub/Sub)')
    mplot._save_or_show(c)
```

<img src="figures/ztf-ztf-20210914.png" alt=""/>

<img src="figures/alerts-ztf-20210914.png" alt=""/>

<img src="figures/BigQuery-ztf-20210914.png" alt=""/>

<img src="figures/alert_avros-ztf-20210914.png" alt=""/>

<img src="figures/SuperNNova-ztf-20210914.png" alt=""/>


## figures_OG

```python
import figures_OG as figs

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


```python
from matplotlib import pyplot as plt
import figures as figs

query = {
    'survey': 'ztf',
    'testid': False,
    'date': '20210907',
    # 'limit': 100,
}
# mplot = figs.MetadataPlotter(query=query, savefig_dir=savefig_dir)
mplot = figs.MetadataPlotter(df=mplot.df, savefig_dir=savefig_dir)

fig = plt.figure()
ax = fig.gca()
compare_cols = ['alert_avros']
bin_per='min'
mplot._plot_incoming_rate_hist(ax, bin_per=bin_per, compare_cols=compare_cols)
plt.show(block=False)

```

## JOIN tables

```python
metacols = [
    'kafka_timestamp__alerts',
    'publish_time__alerts',
    'publish_time__BigQuery',
    'publish_time__alert_avros',
    'publish_time__exgalac_trans_cf',
    'publish_time__SuperNNova',
]
sourcecols = [
    'jd',
]
joinon = 'candid'
kafka_topic = 'ztf_20210916_programid1'

query = (
    f"WITH metadata AS "
        f"(SELECT {','.join(metacols)}, {joinon} "
        f"FROM `{project_id}.{dataset}.metadata` "
        f"WHERE kafka_topic__alerts='{kafka_topic}'), "
    f"source AS "
        f"(SELECT {','.join(sourcecols)}, {joinon} "
        f"FROM `{project_id}.{dataset}.DIASource`) "
    f"SELECT {','.join([f'm.{m}' for m in metacols])}, "
    f"{','.join([f's.{s}' for s in sourcecols])} "
    f"FROM metadata as m "
    f"INNER JOIN source as s "
    f"ON m.candid = CAST(s.candid AS STRING)"
)

mpjd = figs.MetadataPlotter(query=query, savefig_dir=savefig_dir)
# mpjd = figs.MetadataPlotter(df=mpjd.df, query=query, savefig_dir=savefig_dir)

mpjd.df['publish_time__jd'] = pd.to_datetime(
    mpjd.df['jd'], unit="D", origin='julian', utc=True
)

cols = ['jd', 'alerts', 'BigQuery', 'alert_avros', 'exgalac_trans_cf', 'SuperNNova']
for c in cols:
fig = plt.figure()
gs = fig.add_gridspec(2, 2,  width_ratios=(7, 1.3), height_ratios=(2, 7),
                      left=0.1, right=0.9, bottom=0.1, top=0.9,
                      wspace=0.05, hspace=0.05)

ax = fig.add_subplot(gs[1, 0])
marg_ax = {
    'x': fig.add_subplot(gs[0, 0], sharex=ax),
    'y': fig.add_subplot(gs[1, 1], sharey=ax),
}
mpjd.plot_proc_time(c, ax, clip_first=clip_first, marg_ax=marg_ax)
fig.autofmt_xdate()
fig.suptitle(f"{c.split('__')[-1]}")
mpjd._save_or_show(c)
plt.close(fig)

```
