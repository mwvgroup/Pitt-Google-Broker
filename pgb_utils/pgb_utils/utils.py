#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``utils`` contains functions that facilitate interacting with
Pitt-Google Broker's data and services.
"""


def ztf_fid_names() -> dict:
    """Return a dictionary mapping the ZTF `fid` (filter ID) to the common name."""
    return {1: "g", 2: "r", 3: "i"}
