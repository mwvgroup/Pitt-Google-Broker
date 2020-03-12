#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Script to ingest the ZTF alert stream to GCS"""

import os
from datetime import datetime

from pgbroker.consumer import GCSKafkaConsumer

# Define connection configuration using default values as a starting point
config = {
    'bootstrap.servers': os.getenv('ztf_server'),
    'group.id': 'group',
    'session.timeout.ms': 6000,
    'enable.auto.commit': 'FALSE',
    'sasl.kerberos.kinit.cmd': 'kinit -t "%{sasl.kerberos.keytab}" -k %{sasl.kerberos.principal}',
    'sasl.kerberos.service.name': 'kafka',
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.mechanisms': 'GSSAPI',
    'auto.offset.reset': 'earliest',
    'sasl.kerberos.principal': os.getenv('ztf_principle'),
    'sasl.kerberos.keytab': os.getenv('ztf_keytab_path'),
}

# Each ZTF topic is its own date
now = datetime.now()
ztf_topic = f'ztf_{now.year}{now.month:02d}{now.day:02d}_programid1'

# Create a consumer
c = GCSKafkaConsumer(
    kafka_config=config,
    bucket_name='ztf_avro_files',
    kafka_topic=ztf_topic,
    pubsub_topic='ztf_avro_status'
)

if __name__ == '__main__':
    c.run()  # Ingest alerts one at a time indefinitely
