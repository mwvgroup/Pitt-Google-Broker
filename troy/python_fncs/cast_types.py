# !/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Functions for casting between different data types and formats.

Base developed by Daniel Perrafort.
"""

from base64 import b64decode, b64encode
import fastavro
from io import BytesIO
import json
from urllib.parse import urlencode

from astropy.time import Time
from django import template

register = template.Library()


def bytes_to_64utf8(bytes_data):
    """Convert bytes data to UTF8.

    Args:
        bytes_data (bytes): Bytes data

    Returns:
        A string in UTF-8 format
    """
    if bytes_data is not None:
        return b64encode(bytes_data).decode('utf-8')


def base64_to_dict(bytes_data):
    """Convert base64 encoded bytes data to a dict.

    Args:
        bytes_data (base64 bytes): base64 encoded bytes

    Returns:
        A dictionary
    """
    if bytes_data is not None:
        return json.loads(b64decode(bytes_data).decode("utf-8"))


def avro_to_dict(bytes_data):
    """Convert Avro serialized bytes data to a dict.

    Args:
        bytes_data (bytes): Avro serialized bytes

    Returns:
        A dictionary
    """
    if bytes_data is not None:
        with BytesIO(bytes_data) as fin:
            alert_dicts = [r for r in fastavro.reader(fin)]  # list with single dict
        return alert_dicts[0]


def b64avro_to_dict(bytes_data):
    """Convert base64 encoded, Avro serialized bytes data to a dict.

    Args:
        bytes_data (bytes): base64 encoded, Avro serialized bytes

    Returns:
        A dictionary
    """
    if bytes_data is not None:
        with BytesIO(b64decode(bytes_data)) as fin:
            alert_dicts = [r for r in fastavro.reader(fin)]  # list with single dict
        return alert_dicts[0]


def jd_to_readable_date(jd):
    """Convert a julian date to a human readable string.

    Args:
        jd (float): Datetime value in julian format

    Returns:
        String in 'day mon year hour:min' format
    """
    return Time(jd, format='jd').strftime("%d %b %Y - %H:%M:%S")


def urlparams(**kwargs):
    """Format keyword arguments as url parameters.

    Returns:
        A string in the format '?<key>=<value>'
    """
    safe_args = {k: v for k, v in kwargs.items() if v is not None}
    if safe_args:
        return '?{}'.format(urlencode(safe_args))

    return ''
