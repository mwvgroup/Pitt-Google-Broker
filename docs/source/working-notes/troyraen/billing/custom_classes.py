#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from collections import namedtuple


# LOAD PRE-QUEREIED DATA FROM FILE
# class to hold objects returned by load_countdf_litebilldf_from_file
loaded_data = namedtuple("loaded_data", "countdf, litebilldf, litebill_ispipelinesku")
