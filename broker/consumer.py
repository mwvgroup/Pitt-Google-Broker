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
       kafka_topic='my_kafka_topic_name',
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
from warnings import warn

from confluent_kafka import Consumer, KafkaException

if not os.getenv('GPB_OFFLINE', False):
    from google.cloud import pubsub, storage
    from google.cloud.pubsub_v1.publisher.futures import Future

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


class TempAlertFile(SpooledTemporaryFile):
    """Subclass of SpooledTemporaryFile that is tied into the log"""

    def rollover(self) -> None:
        """Move contents of the spooled file from memory onto disk"""

        log.warning(f'Alert size exceeded max memory size: {self._max_size}')
        super().rollover()


def _set_config_defaults(kafka_config: dict) -> dict:
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
            msg = f'Config value {key} passed as {config_val} - changing to `{default_value}`'
            warn(msg)
            log.warning(msg)
            kafka_config.setdefault('enable.auto.commit', 'FALSE')

    return kafka_config


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

        Storage bucket and PubSub topic must already exist and have
        appropriate permissions.

        Args:
            kafka_config: Kafka consumer configuration properties
            kafka_topic: Kafka topics to subscribe to
            bucket_name: Name of the bucket to upload into
            pubsub_topic: PubSub topic to publish to
            debug: Run without committing Kafka position
        """

        self._debug = debug
        self.kafka_topic = kafka_topic
        self.bucket_name = bucket_name
        self.pubsub_topic = pubsub_topic
        self.kafka_server = kafka_config["bootstrap.servers"]
        log.info(f'Initializing consumer: {self.__repr__()}')

        # Connect to Kafka stream
        # Enforce NO auto commit, correct log handling
        super().__init__(_set_config_defaults(kafka_config))
        self.subscribe([kafka_topic])

        # Connect to Google Cloud Storage
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.get_bucket(bucket_name)
        log.info(f'Connected to bucket: {self.bucket.name}')

        # Configure PubSub topic
        project_id = os.getenv('BROKER_PROJ_ID')
        self.publisher = pubsub.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, pubsub_topic)

        # Raise error if topic does not exist
        self.topic = self.publisher.get_topic(self.topic_path)
        log.info(f'Connected to PubSub: {self.topic_path}')

    def close(self) -> None:
        """Close down and terminate the Kafka Consumer"""

        log.info(f'Closing consumer: {self.__repr__()}')
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
        max_alert_packet_size = 150000
        with SpooledTemporaryFile(max_size=max_alert_packet_size, mode='w+b') as temp_file:
            temp_file.write(data)
            temp_file.seek(0)
            blob.upload_from_file(temp_file)

    def publish_pubsub(self, message: str) -> Future:
        """Publish a PubSub alert

        Args:
            message: The message to publish

        Returns:
            The Id of the published message
        """

        log.debug(f'Publishing message: {message}')
        message_data = message.encode('UTF-8')
        future = self.publisher.publish(self.topic_path, data=message_data)
        return future.result()

    def run(self) -> None:
        """Ingest kafka Messages to GCS and PubSub"""

        log.info('Starting consumer.run ...')
        try:
            while True:
                msg = self.consume(num_messages=1, timeout=5)
                if msg is None:
                    continue

                if msg.error():
                    err_data = (msg.topic(), msg.partition(), msg.offset(), msg.key(), msg.error())
                    err_msg = 'KafkaException for {} [{}] at offset {} with key {}:\n  %%  {}'.format(*err_data)
                    log.error(err_msg, exc_info=True)
                    raise KafkaException(msg.error())

                else:
                    timestamp_kind, timestamp = msg.timestamp()
                    file_name = f'{timestamp}.avro'

                    log.debug(f'Ingesting {file_name}')
                    self.upload_bytes_to_bucket(msg.value(), file_name)
                    self.publish_pubsub(file_name)
                    if not self._debug:
                        self.commit()

        except KeyboardInterrupt:
            log.error('User ended consumer', exc_info=True)
            raise

        except Exception as e:
            log.error(f'Consumer level error: {e}', exc_info=True)
            raise

    def __repr__(self) -> str:
        return (
            '<Consumer('
            f'kafka_server: {self.kafka_server}, '
            f'kafka_topic: {self.kafka_topic}, '
            f'bucket_name: {self.bucket_name}, '
            f'pubsub_topic: {self.pubsub_topic}'
            ')>'
        )
