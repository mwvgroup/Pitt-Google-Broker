#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Pitt-Google types."""

from dataclasses import dataclass
import logging
from typing import NamedTuple, Union

from .schema_maps import get_key, get_value


logger = logging.getLogger(__name__)


class _AlertIds(NamedTuple):
    """Simple class for IDs associated with an alert."""

    sourceId: Union[str, int, float, None] = None
    objectId: Union[str, int, float, None] = None


@dataclass
class AlertFilename:
    """Filename of an alert stored to a Cloud Storage bucket."""

    class ParsedFilename(NamedTuple):
        """Component parts of an ``AlertFilename``."""

        objectId: Union[str, int, float, None] = None
        sourceId: Union[str, int, float, None] = None
        topic: Union[str, None] = None
        format: str = "avro"

    def __init__(self, aname: Union[str, dict]):
        """Set self.name to the filename and self.parsed to a ``ParsedFilename``.

        Args
            aname:
                If str, full filename of the alert.
                If dict, components to create the filename. Required key/value pairs
                are those needed to create a ``ParsedFilename``.
                Extra keys are ignored.
        """
        if isinstance(aname, str):
            self.name = aname
            self.parsed = self.ParsedFilename._make(aname.split("."))

        elif isinstance(aname, dict):
            self.parsed = self.ParsedFilename(
                **dict(
                    (k, v) for k, v in aname.items() if k in self.ParsedFilename._fields
                )
            )
            self.name = ".".join(str(i) for i in self.parsed)


@dataclass
class AlertIds:
    """IDs associated with an alert."""

    def __init__(self, schema_map, **kwargs):
        """Initialize class instance.

        kwargs will be sent to `self.extract_ids()` and may contain keys:
            alert_dict, attrs, filename
        """
        self.schema_map = schema_map

        if any(key in kwargs for key in ["alert_dict", "attrs", "filename"]):
            self._ids = self.extract_ids(**kwargs)
        else:
            self._ids = None

        self._id_keys = None
        self._sourceId = None
        self._objectId = None

    @property
    def ids(self):
        """Alert IDs."""
        if self._ids is None:
            logger.warning(
                (
                    "No IDs have been set. Please call the extract_ids() method or "
                    "reinitialize with appropriate data."
                )
            )
        return self._ids

    def extract_ids(self, alert_dict=None, attrs=None, filename=None, **kwargs):
        """Extract IDs to an `_AlertIds` object and return it.

        Attempts to extract IDs from alert_dict, attrs, and filename, in that order.
        kwargs are ignored and only provided for the caller's convenience.
        """
        if alert_dict is not None:
            ids = _AlertIds(
                get_value("sourceId", alert_dict, self.schema_map),
                get_value("objectId", alert_dict, self.schema_map),
            )

        elif attrs is not None:
            id_keys = self.id_keys
            ids = _AlertIds(
                attrs.get(id_keys.sourceId), attrs.get(id_keys.objectId)
            )

        elif filename is not None:
            parsed = AlertFilename(filename).parsed
            ids = _AlertIds(parsed.sourceId, parsed.objectId)

        return ids

    @property
    def id_keys(self):
        """Return the ID key names used by the survey."""
        if self._id_keys is None:
            self._id_keys = _AlertIds(
                get_key("sourceId", self.schema_map),
                get_key("objectId", self.schema_map),
            )
        return self._id_keys

    @property
    def sourceId(self):
        """Return the sourceId."""
        if self._sourceId is None:
            self._sourceId = self.ids.sourceId
        return self._sourceId

    @property
    def objectId(self):
        """Return the objectId."""
        if self._objectId is None:
            self._objectId = self.ids.objectId
        return self._objectId
