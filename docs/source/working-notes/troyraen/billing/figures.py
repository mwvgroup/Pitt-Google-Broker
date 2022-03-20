#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Make billing figures."""
from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FormatStrFormatter


def usetex(usetex):
    """Set pyplot rcParams text.usetex. Controls whether plots are formatted using Tex.

    If usetex is true, we must use math mode ($$) and escape special characters.
    """
    fontsize = 18 if usetex else 13
    plt.rcParams.update({
        "text.usetex": usetex,
        "font.size": fontsize,
    })


ALL_SERVICES = (
    'App Engine',
    'BigQuery',
    'Cloud Build',
    'Cloud Dataflow',
    'Cloud Functions',
    'Cloud Logging',
    'Cloud Pub/Sub',
    'Cloud Run',
    'Cloud Scheduler',
    'Cloud SQL',
    'Cloud Storage',
    'Compute Engine',
    'Invoice',
    'Stackdriver Monitoring',
)

SERVICES = (
    'BigQuery',
    'Cloud Dataflow',
    'Cloud Functions',
    'Cloud Pub/Sub',
    'Cloud Run',
    'Cloud SQL',
    'Cloud Scheduler',
    'Cloud Storage',
    'Compute Engine',
)

cmap_color_list = cm.get_cmap('tab20').colors
ALL_SERVICE_COLORS = {service: cmap_color_list[i] for i, service in enumerate(ALL_SERVICES)}
cmap_color_list = cm.get_cmap('Set1').colors
cmap_color_list = (cmap_color_list[1:] + (cmap_color_list[0], ))  # move red to the back
SERVICE_COLORS = {service: cmap_color_list[i] for i, service in enumerate(SERVICES)}


def _service_color(service):
    return ALL_SERVICE_COLORS[service]


def plot_cost_by_sku(costdf, cost='cost', save=None, title=None, usetex=False):
    """Plot bar chart of cost vs short_sku, colored by service.

    Args:
        costdf (pd.DataFrame):
            As returned by transforms.cost_by_sku()

        cost (str):
            Name of the cost column to plot
    """
    usetex = plt.rcParams["text.usetex"]
    # colors and legend
    colorby = 'service'
    colors = tuple(_service_color(service) for service in costdf[colorby])
    legend_elements = [
        Patch(color=ALL_SERVICE_COLORS[s], label=s) for s in costdf[colorby].unique()
    ]

    fig = plt.figure(figsize=(13, 8))
    ax = fig.gca()
    costdf.plot.bar(x='short_sku', y=cost, rot=90, color=colors, ax=ax)

    # annotate with number of alerts received
    labels = round(costdf[cost], 2)  # height of each bar
    y_offset = 0.25  # put space between bar and text
    for i, label in enumerate(labels):
        lbl = fr'\${label:.2f}' if usetex else f'${label:.2f}'
        ax.text(i, label + y_offset, lbl, ha='center', rotation='horizontal')

    plt.legend(handles=legend_elements)
    plt.xlabel(" ")
    plt.ylabel(f"{cost.replace('_', ' ')} (USD)")
    fmt = r'\$%.2f' if usetex else '$%.2f'
    ax.yaxis.set_major_formatter(FormatStrFormatter(fmt))
    plt.title(title)
    plt.tight_layout()

    if save:
        plt.savefig(save)
    else:
        plt.show(block=False)


def _format_daterange():
