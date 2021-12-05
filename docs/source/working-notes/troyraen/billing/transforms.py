#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Transform billing data."""
from collections import namedtuple
import re


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
