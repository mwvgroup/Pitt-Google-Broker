#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""The ``consumer`` module handles the ingestion of a Kafka alert stream into
Google Cloud Storage (GCS) and defines default connection settings for
different Kafka servers.

Usage Example
-------------

.. code-block:: python
   :linenos:

   from broker.consumer import GCSKafkaConsumer, DEFAULT_ZTF_CONFIG

   # Define connection configuration using default values as a starting point
   config = DEFAULT_ZTF_CONFIG.copy()
   config['sasl.kerberos.keytab'] = '<Path to authentication file>'
   config['sasl.kerberos.principal'] = '<>'
   print('Connecting with config values:\n\n', config)

   # Create a consumer
   c = GCSKafkaConsumer(
       kafka_config=config,
       bucket_name='my-GCS-bucket-name',
       kafka_topics='ztf_20200301_programid1',
       pubsub_topic='my-GCS-PubSub-name',
       debug=True  # Use debug to run without updating your kafka offset
   )

   # Ingest alerts one at a time indefinitely
   c.run()


Module Docs
-----------
"""

import logging
import os
from tempfile import SpooledTemporaryFile
from warnings import warn

from confluent_kafka import Consumer, KafkaException
from google.cloud import pubsub_v1, storage

log = logging.Logger(__name__)
__names__ = ['DEFAULT_ZTF_CONFIG', 'GCSKafkaConsumer']

DEFAULT_ZTF_CONFIG = {
    'bootstrap.servers': 'public2.alerts.ztf.uw.edu:9094',
    'group.id': 'group',
    'session.timeout.ms': 6000,
    'enable.auto.commit': 'FALSE',
    'sasl.kerberos.kinit.cmd': 'kinit -t "%{sasl.kerberos.keytab}" -k %{sasl.kerberos.principal}',
    'sasl.kerberos.service.name': 'kafka',
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.mechanisms': 'GSSAPI',
    'auto.offset.reset': 'earliest'
    # User authentication
    # 'sasl.kerberos.principal':
    # 'sasl.kerberos.keytab':
}


class GCSKafkaConsumer(Consumer):
    """Ingests data from a kafka stream into big_query"""

    def __init__(self, kafka_config, bucket_name, kafka_topic,
                 pubsub_topic, debug=False):
        """Ingests data from a kafka stream into big_query

        Args:
            kafka_config (dict): Kafka consumer configuration properties
            bucket_name   (str): Name of the bucket to upload into
            kafka_topic   (str): Kafka topics to subscribe to
            pubsub_topic  (str): PubSub topic to publish to
            debug        (bool): Run without committing Kafka position
        """

        self.debug = debug
        self.server = kafka_config["bootstrap.servers"]
        log.info(f'Instantiating consumer for {self.server}')

        # Enforce NO auto commit
        commit_config = kafka_config.get('enable.auto.commit', None)
        if commit_config != 'FALSE':
            warn(f'enable.auto.commit set to {commit_config} - changing to `False`')
            kafka_config.setdefault('enable.auto.commit', 'FALSE')

        # Connect to Kafka stream
        super().__init__(kafka_config)
        self.subscribe([kafka_topic])

        # Connect to Google Cloud
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.get_bucket(bucket_name)

        # Configure PubSub
        project_id = os.getenv('BROKER_PROJ_ID')
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, pubsub_topic)

    def close(self):
        """Close down and terminate the Kafka Consumer"""

        log.info(f'Closing consumer for {self.server}')
        super().close()

    def upload_bytes_to_bucket(self, bytes, destination_name):
        """Uploads bytes data to a GCP storage bucket

        Args:
            bytes          (bytes): Data to upload
            destination_name (str): Name of the file to be created
        """

        log.debug(f'Uploading file to {destination_name}')
        blob = self.bucket.blob(destination_name)

        # By default, spool data in memory to avoid IO unless data is too big
        with SpooledTemporaryFile() as temp_file:
            temp_file.write(bytes)
            temp_file.seek(0)
            blob.upload_from_file(temp_file)

    def publish_pubsub(self, message):
        """Publish a PubSub alert

        Args:
            message (str): The message to publish

        Returns:
            The Id of the published message
        """

        message_data = message.encode('UTF-8')
        future = self.publisher.publish(self.topic_path, data=message_data)
        return future.result()

    def run(self):
        """Ingest kafka Messages to GCS and PubSub"""

        log.info('Starting consumer.run ...')
        try:
            while True:
                msg = self.poll(timeout=5)
                if msg is None:
                    continue

                if msg.error():
                    err_msg = '{} [{}] at offset {} with key {}:\n  %%  {}'
                    err_data = (msg.topic(), msg.partition(), msg.offset(), msg.key(), msg.error())
                    log.error(err_msg.format(err_data))
                    raise KafkaException(msg.error())

                else:
                    timestamp_kind, timestamp = msg.timestamp()
                    assert timestamp_kind == 1
                    file_name = f'{timestamp}.avro'

                    log.debug(f'Ingesting {file_name}')
                    self.upload_bytes_to_bucket(msg.value(), file_name)
                    self.publish_pubsub(file_name)
                    if not self.debug:
                        self.commit()

        except KeyboardInterrupt:
            log.error('User ended consumer')
            raise

        except Exception as e:
            log.error(f'Consumer level error: {e}')
            raise
