#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Pull files from a Cloud Storage bucket and publish them to a Pub/Sub topic.

One message per file.
The bucket, Pub/Sub topic, and publish format (Avro or JSON) are configurable via the
Pub/Sub message used to trigger the service.
"""
