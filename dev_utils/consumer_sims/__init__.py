#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``consumer_sim`` module simulates the broker's consumer component by publishing alerts to a testing instance of the Pub/Sub topic ztf_alerts.
It gets the alerts from a Pub/Sub subscription (ztf_alerts-reservoir) on the production instance of the ztf_alerts topic, which acts as a reservoir from which we can control the timing/flow rate of alerts into a testing instance of the broker.
"""
