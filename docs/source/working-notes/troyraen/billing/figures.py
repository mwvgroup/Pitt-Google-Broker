#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Make billing figures."""
from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib.patches import Patch

ALL_SERVICES = (
    'App Engine',
    'BigQuery',
    'Cloud Build',
    'Cloud Dataflow',
    'Cloud Functions',
    'Cloud Logging',
    'Cloud Pub/Sub',
    'Cloud Run',
    'Cloud SQL',
    'Cloud Scheduler',
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


def plot_cost_by_sku(costdf, cost='cost', save=None, title=None):
    """Plot bar chart of cost vs short_sku, colored by service.

    Args:
        costdf (pd.DataFrame):
            As returned by transforms.cost_by_sku()

        cost (str):
            Name of the cost column to plot
    """
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
        ax.text(i, label + y_offset, label, ha='center', rotation='horizontal')

    plt.legend(handles=legend_elements)
    plt.ylabel(f"{cost} (USD)")
    plt.title(title)
    plt.tight_layout()

    if save:
        plt.savefig(save)
    else:
        plt.show(block=False)
