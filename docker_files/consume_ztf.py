#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Script to ingest the ZTF alert stream to GCS"""

import os
from datetime import datetime

from broker.alert_ingestion.consume import GCSKafkaConsumer

# Define connection configuration using default values as a starting point
config = {
    'bootstrap.servers': os.environ['ztf_server'],
    'group.id': 'group',
    'session.timeout.ms': 6000,
    'enable.auto.commit': 'FALSE',
    'sasl.kerberos.kinit.cmd': 'kinit -t "%{sasl.kerberos.keytab}" -k %{sasl.kerberos.principal}',
    'sasl.kerberos.service.name': 'kafka',
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.mechanisms': 'GSSAPI',
    'auto.offset.reset': 'earliest',
    'sasl.kerberos.principal': os.environ['ztf_principle'],
    'sasl.kerberos.keytab': os.environ['ztf_keytab_path'],
}

# Each ZTF topic is its own date
now = datetime.now()
ztf_topic = f'ztf_{now.year}{now.month:02d}{now.day:02d}_programid1'

# Create a consumer
c = GCSKafkaConsumer(
    kafka_config=config,
    bucket_name='ardent-cycling-243415_ztf_alert_avro_bucket',
    kafka_topic=ztf_topic,
    pubsub_alert_data_topic='ztf_alert_data',
    pubsub_in_GCS_topic='ztf_alert_avro_in_bucket'
)

if __name__ == '__main__':
    c.run()  # Ingest alerts one at a time indefinitely
