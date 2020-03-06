#!/usr/bin/env python3
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
   print(config)

   # Create a consumer
   c = GCSKafkaConsumer(
       kafka_config=config,
       bucket_name='my-gcs-bucket-name',
       kafka_topic='ztf_20200301_programid1',
       pubsub_topic='my-gcs-pubsub-name',
       debug=True  # Use debug to run without updating your kafka offset
   )

   # Ingest alerts one at a time indefinitely
   c.run()


Module Documentation
--------------------
"""

import logging
import os
from tempfile import SpooledTemporaryFile

from confluent_kafka import Consumer, KafkaException
from google.cloud import pubsub_v1, storage

from .exceptions import CloudConnectionError

log = logging.getLogger(__name__)

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


def set_config_defaults(kafka_config: dict) -> dict:
    """Set default values for a Kafka configuration dictionary

    Default values:
        enable.auto.commit: False,
        logger: log

    Args:
        kafka_config: Dictionary of config values

    Returns:
        A copy of the passed configuration dictionary set with default values
    """

    kafka_config = kafka_config.copy()
    default_vals = {'enable.auto.commit': False, 'logger': log}
    for key, default_value in default_vals.items():
        config_val = kafka_config.get(key, None)
        if config_val != default_value:
            log.warning(f'Config value {key} set to {config_val} - changing to `{default_value}`')
            kafka_config.setdefault('enable.auto.commit', 'FALSE')

    return kafka_config


class TempAlertFile(SpooledTemporaryFile):
    """Subclass of SpooledTemporaryFile that is tied into the log"""

    def rollover(self):
        """Move contents of the spooled file from memory onto disk"""

        log.warning(f'Alert size exceeded max memory size: {self._max_size}')
        super().rollover()


class GCSKafkaConsumer(Consumer):
    """Ingests data from a kafka stream into big_query"""

    def __init__(
            self,
            kafka_config: dict,
            kafka_topic: str,
            bucket_name: str,
            pubsub_topic: str,
            debug: bool = False):
        """Ingests data from a kafka stream and stores a copy in GCS

        Args:
            kafka_config (dict): Kafka consumer configuration properties
            kafka_topic   (str): Kafka topics to subscribe to
            bucket_name   (str): Name of the bucket to upload into
            pubsub_topic  (str): PubSub topic to publish to
            debug        (bool): Run without committing Kafka position
        """

        self.debug = debug
        self.server = kafka_config["bootstrap.servers"]
        log.info(f'Instantiating consumer for {self.server}')

        # Enforce NO auto commit, correct log handling
        kafka_config = set_config_defaults(kafka_config)

        # Connect to Kafka stream
        super().__init__(kafka_config)
        self.subscribe([kafka_topic])

        # Connect to Google Cloud Storage
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.get_bucket(bucket_name)

        # Configure PubSub topic
        project_id = os.getenv('BROKER_PROJ_ID')
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, pubsub_topic)

    # Todo: raise error if kafka not authenticated
    # Todo: may want to raise error if pubsub topic is not defined
    def _check_connection(self):

        if not self.bucket.exists():
            msg = f'Bucket {self.bucket.name} does not exist'
            log.error(msg, exc_info=True)
            raise CloudConnectionError(msg)

        log.info(f'Connected to bucket: {self.bucket.name}')  # Todo raise error if bucket does not exist
        log.info(f'Connected to PubSub: {self.topic_path}')  # Todo raise error if topic does not exist

    def close(self):
        """Close down and terminate the Kafka Consumer"""

        log.info(f'Closing consumer for {self.server}')
        super().close()

    def upload_bytes_to_bucket(self, data: bytes, destination_name: str):
        """Uploads bytes data to a GCP storage bucket

        Args:
            data: Data to upload
            destination_name: Name of the file to be created
        """

        log.debug(f'Uploading {destination_name} to {self.bucket.name}')
        blob = self.bucket.blob(destination_name)

        # By default, spool data in memory to avoid IO unless data is too big
        # LSST alerts are anticipated at 80 kB, so 150 kB should be plenty
        with SpooledTemporaryFile(max_size=150000, mode='w+b') as temp_file:
            temp_file.write(data)
            temp_file.seek(0)
            blob.upload_from_file(temp_file)

    def publish_pubsub(self, message: str):
        """Publish a PubSub alert

        Args:
            message: The message to publish

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
                    # todo: These time stamp values are huge. Why?
                    timestamp_kind, timestamp = msg.timestamp()
                    assert timestamp_kind == 1  # Todo: don't use assert
                    file_name = f'{timestamp}.avro'

                    log.debug(f'Ingesting {file_name}')
                    self.upload_bytes_to_bucket(msg.value(), file_name)
                    self.publish_pubsub(file_name)
                    if not self.debug:
                        self.commit()

        except KeyboardInterrupt:
            log.error('User ended consumer', exc_info=True)
            raise

        except Exception as e:
            log.error(f'Consumer level error: {e}', exc_info=True)
            raise
