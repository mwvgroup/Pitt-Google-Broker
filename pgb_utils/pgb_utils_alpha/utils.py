#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``utils`` contains functions that facilitate interacting with
Pitt-Google Broker's data and services.
"""

def alert_dict_to_dataframe(alert):
    """ Packages an alert into a dataframe.
    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    dfc = pd.DataFrame(alert['candidate'], index=[0])
    df_prv = pd.DataFrame(alert['prv_candidates'])
    dflc = pd.concat([dfc,df_prv], ignore_index=True)

    # we'll attach some metadata--not this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    dflc.objectId = alert['objectId']
    dflc.candid = alert['candid']
    return dflc
