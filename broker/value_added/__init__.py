#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""The ``value_added`` module retrieves/calculates and provides access
to all value added products (e.g. classification, cross matches, etc.)
"""

from .classify import rapid
from .xmatch import get_xmatches
from .value_added import get_value_added
