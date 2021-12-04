#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


def shorten_sku(sku):
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
            'Storage Frankfurt',
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
