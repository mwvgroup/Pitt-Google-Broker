#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``format_alerts`` module handles formatting inconsistencies between
incoming alerts streams an big query.

Usage Example
-------------

Alerts can be formatted for BigQuery compliance using the ``formatted_alert``
function. For example, to format a ZTF alert with schema version 3.3:

.. code-block:: python
   :linenos:

   from broker.alert_ingenstion import format_alerts

   formatted_alert = format_alert_schema(b'this is some alert data', survey='ztf', version=3.3)

If you don't know the survey or schema version of the alert, either of the
``survey`` or ``version`` arguments can be omitted and ``format_alert_schema``
will try to guess the appropriate values from the alert content. If you wish
to check the inferred value of these parameters (e.g., for debugging purposes),
this functionality is accessible via dedicated functions:

.. code-block:: python
   :linenos:

   from broker.alert_ingenstion import format_alerts

   alerts_bytes = b'this is some more alert data`
   guessed_survey = guess_schema_survey(alerts_bytes)
   guessed_version = guess_schema_version(alerts_bytes)


Module Documentation
--------------------
"""

import logging
import re

from ..exceptions import SchemaParsingError

log = logging.getLogger(__name__)


def _format_ztf_3_3(alert_bytes: bytes) -> bytes:
    """Format a ZTF alert with schema version 3.7 for BigQuery compatibility

    Imposed changes:
        - Todo: list changes here

    Args:
        alert_bytes: An alert from ZTF or LSST

    Returns:
        A bytes object representing the formatted alert
    """

    re.sub(b'old_bytes', b'new_bytes', alert_bytes)
    return alert_bytes


def guess_schema_version(alert_bytes: bytes) -> float:
    """Retrieve the ZTF schema version

    Args:
        alert_bytes: An alert from ZTF or LSST

    Returns:
        The schema version
    """

    version_regex_pattern = b"(schema_vsn=')([0-9]*\.[0-9]*)(')"
    version_match = re.match(version_regex_pattern, alert_bytes)
    if version_match is None:
        err_msg = f'Could not guess schema vsersion for alert {alert_bytes}'
        log.error(err_msg)
        raise SchemaParsingError(err_msg)

    return float(version_match.group(2))


def guess_schema_survey(alert_bytes: bytes) -> str:
    """Retrieve the ZTF schema version

    Args:
        alert_bytes: An alert from ZTF or LSST

    Returns:
        The survey name
    """

    survey_regex_pattern = b"(survey=')(\S*)(')"
    survey_match = re.match(survey_regex_pattern, alert_bytes)
    if survey_match is None:
        err_msg = f'Could not guess survey name for alert {alert_bytes}'
        log.error(err_msg)
        raise SchemaParsingError(err_msg)

    return survey_match.groups(2).decode()


def format_alert_schema(
        alerts_bytes: bytes, survey: str = None, version: float = None) -> bytes:
    """Format an alert to be compatible with upload to Big Query

    The survey name and / or schema version is guessed from the alert if not
    provided.

    Args:
        alerts_bytes: The alert object to format
        survey: The name of the survey the alert is from (optional)
        version: The schema version of the alert is from (optional)

    Return:
        A copy of the bytes object with a modified schema
    """

    if survey is None:
        survey = guess_schema_survey(alerts_bytes)

    if version is None:
        version = guess_schema_version(alerts_bytes)

    format_funcs = {
        'ztf': {
            3.3: _format_ztf_3_3
        }
    }

    try:
        format_func = format_funcs.get(survey, {})[version]

    except IndexError:
        err_msg = f'Formatting not available for {survey} {version}'
        log.error(err_msg)
        raise RuntimeError(err_msg)

    else:
        return format_func(alerts_bytes)
