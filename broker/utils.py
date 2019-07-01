#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""General utilities for common tasks performed across the ``broker`` package.
"""

import logging

import google.cloud as gcp


def setup_log(log_name, level='INFO'):
    """Create a logging object connected to google cloud

    Args:
        log_name (str): Name of the logger
        level    (str): Reporting level for the log

    Returns:
        A Logger object, or None
    """

    log = logging.Logger(log_name)
    log.setLevel(level)

    # Connect to GCP
    logging_client = gcp.logging.Client()
    handler = logging_client.get_default_handler()
    log.addHandler(handler)

    return log
