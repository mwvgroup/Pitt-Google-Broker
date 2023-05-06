#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Transform billing data."""
from collections import namedtuple
import datetime
import pandas as pd
import re

from custom_classes import loaded_data


PROD_PROJECT_ID = "ardent-cycling-243415"

SPECIAL_DATES = {
    "testing": [
        # Remove testing costs that significantly impact the mean
        # AllWISE crossmatch queried BigQuery for every alert
        datetime.date(2021, 9, 26),
        datetime.date(2021, 9, 27),
        datetime.date(2021, 9, 28),
    ],
    "lsst-like-rates": [
        # On Sept 23, 2021 ZTF dumped alerts at LSST rates
        datetime.date(2021, 9, 23),
    ]
}

ServiceSkus = namedtuple('ServiceSkus', 'service skus')

# Skus associated with running the live data pipeline
# Other skus are storage and admin related
PIPELINE_SKUS = (
    ServiceSkus("BigQuery", [r"Streaming Insert", r"Analysis"]),
    ServiceSkus("Cloud Logging", [r"."]),
    ServiceSkus(
        "Cloud Pub/Sub",
        [
            r"Message Delivery Basic",
            r"Inter-region data delivery",
            r"Intra-region data delivery",
            r"Internet data delivery",
        ]
    ),
    ServiceSkus("Compute Engine", [r"."]),
    ServiceSkus("Cloud Dataflow", [r"."]),
    ServiceSkus("Cloud Functions", [r"."]),
    ServiceSkus("Cloud Run", [r"."]),
    ServiceSkus("Cloud Storage", [r"(.+) Class (\w) Operations"])
)


def is_pipeline_sku(billing_row):
    """Return True if this sku is in PIPELINE_SKUS, else False."""
    service = billing_row.service
    sku = billing_row.sku
    is_psku = False

    for ps in PIPELINE_SKUS:
        if service == ps.service:
            for psku in ps.skus:
                if bool(re.match(re.compile(psku), sku)):
                    is_psku = True
    return is_psku


def cost_by_sku(billdf, cost='cost', how='sum', bydate=False):
    """Sum cost by sku and date (if requested), sort, add shortened sku."""
    if bydate:
        keys = ['usage_date', 'service', 'sku']
        sortby = ['usage_date', 'service', cost]
        asc = [True, True, False]
    else:
        keys = ['service', 'sku']
        sortby = ['service', cost]
        asc = [True, False]
    billdf_gb = billdf[keys+[cost]].groupby(keys)
    if how == 'sum':
        costdf = billdf_gb.sum().reset_index()
    elif how == 'mean':
        costdf = billdf_gb.mean().reset_index()

    costdf.sort_values(sortby, ascending=asc, inplace=True)
    costdf['short_sku'] = costdf['sku'].apply(_shorten_sku)
    return costdf


def _shorten_sku(sku):
    skumap = {
        'Inter-region data delivery from North America to North America':
            'Inter-region delivery',
        'Cloud SQL for MySQL: Zonal - 1 vCPU + 3.75GB RAM in Americas':
            '1 vCPU + 3.75GB RAM',
        'Cloud SQL for MySQL: Zonal - Standard storage in Americas':
            'Standard storage',
        'Standard Storage US Multi-region':
            'Standard Storage',
        'Multi-Region Standard Class A Operations':
            'Class A Operations',
        'Multi-Region Standard Class B Operations':
            'Class B Operations',
        'E2 Instance Core running in Americas':
            'E2 Instance Core',
        'E2 Instance Ram running in Americas':
            'E2 Instance Ram',
        'Micro Instance with burstable CPU running in Americas':
            'Micro Instance',
        'Small Instance with 1 VCPU running in Americas':
            'Small Instance',
        'Network Internet Egress from Americas to China':
            'Egress to China',
        'vCPU Time Streaming Iowa':
            'vCPU Time',
        'Streaming data processed for Iowa':
            'Streaming data',
        'Local Disk Time PD Standard Iowa':
            'Local Disk Time',
        'Internet data delivery from North America to North America':
            'Data delivery',
        'Network Internet Egress from Americas to Americas':
            'Egress',
        'External IP Charge on a Standard VM':
            'External IP',
        'Storage PD Capacity in Frankfurt':
            'Storage PD Frankfurt',
        'N2 Instance Core running in Americas':
            'N2 Instance Core',
        'N1 Predefined Instance Core running in Americas':
            'N1 Instance Core',
        'N2 Instance Ram running in Americas':
            'N2 Instance Ram',
        'N1 Predefined Instance Ram running in Americas':
            'N1 Instance Ram',
        'Network Egress via Carrier Peering Network - Americas Based':
            'Egress Americas',
        'Network Inter Region Egress from Americas to Jakarta':
            'Egress to Jakarta',
    }
    return skumap.get(sku, sku)


def calc_cost_per_million(
    ldata: loaded_data,
    cost_col='cost_per_million_alerts_ingested',
    min_cost_per_mil=0.10,
    clean=None,  # [str,] names of special dates to exclude from plot
    show_dates=None,  # [datetime,] dates to plot. if Nonem, plot all
) -> pd.DataFrame:
    """calaculate mean cost per million alerts ingested."""
    countdf, litebilldf, litebill_ispipelinesku = ldata

    # keep rows where project and sku => live pipeline
    mylite_df_indexes = (litebill_ispipelinesku) & (litebilldf["project_id"] == PROD_PROJECT_ID)
    mylitebilldf = litebilldf.loc[mylite_df_indexes]

    # restrict to specific dates, if given
    if show_dates:
        mylitebilldf = mylitebilldf.loc[mylitebilldf.usage_date.isin(show_dates)]

    # remove dates where abnormal things happened affecting costs
    if clean:
        remove_dates = []
        if "testing" in clean:
            remove_dates += SPECIAL_DATES["testing"]
        if "lsst-like-rates" in clean:
            remove_dates += SPECIAL_DATES["lsst-like-rates"]
        mylitebilldf = mylitebilldf.loc[~mylitebilldf.usage_date.isin(remove_dates)]

    # keep only dates with num_alerts > 0
    mylitebilldf = mylitebilldf.set_index('usage_date').sort_index()
    commondates = set(mylitebilldf.index).intersection(set(countdf.index))
    indexes_to_keep = countdf.loc[(countdf.num_alerts>0) & (countdf.index.isin(commondates))].index
    mylitebilldf = mylitebilldf.loc[indexes_to_keep]

    # sum by sku and date
    costdf_bydate = cost_by_sku(mylitebilldf.reset_index(), how='sum', bydate=True)

    # calculate cost per million
    costdf_bydate.set_index('usage_date', inplace=True)
    costdf_bydate[cost_col] = costdf_bydate.cost / countdf.loc[indexes_to_keep].num_alerts * 1e6

    # get average cost/million alerts
    costdf = cost_by_sku(costdf_bydate, cost=cost_col, how='mean')
    # keep only significant costs
    # min_cost_per_mil = 0.10  # passed as an argument
    costdf = costdf.loc[costdf[cost_col] > min_cost_per_mil]

    return costdf


def calc_cost_per_day(
    ldata: loaded_data,
    cost_col='cost_per_day',
    min_cost_per_day=0.01
) -> pd.DataFrame:
    """Calaculate mean cost per day."""
    countdf, litebilldf, litebill_ispipelinesku = ldata
    # keep rows where sku => ~(live pipeline)
    mylitebilldf = litebilldf.loc[~litebill_ispipelinesku]

    # sum by sku and date, then take the mean
    costdf_bydate = cost_by_sku(mylitebilldf.reset_index(), how='sum', bydate=True)
    costdf = cost_by_sku(costdf_bydate, how='mean')
    costdf[cost_col] = costdf["cost"]

    # keep only significant costs
    costdf = costdf.loc[costdf[cost_col] > min_cost_per_day]

    return costdf
