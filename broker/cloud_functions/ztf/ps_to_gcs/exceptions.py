#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Custom exceptions for ps_to_gcs Cloud Function.
"""


class CloudConnectionError(Exception):
    """Error connecting to one or more Google Cloud services"""
    pass


class SchemaParsingError(Exception):
    """Error parsing or guessing properties of an alert schema"""
    pass
