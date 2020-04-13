#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``exceptions`` defines custom exceptions for the parent package

.. autosummary::
   :nosignatures:

Module Documentation
--------------------
"""


class CloudConnectionError(Exception):
    """Error connecting to one or more Google Cloud services"""
    pass


class SchemaParsingError(Exception):
    """Error parsing or guessing properties of an alert schema"""
    pass
