#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""Ingest alerts from a Kafka stream to GCS Storage and PubSub"""

import logging
import os
from tempfile import TemporaryFile
from warnings import warn

from confluent_kafka import Consumer, KafkaException
from google.cloud import pubsub_v1, storage

log = logging.Logger(__name__)

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

    def __init__(self, kafka_config, bucket_name, kafka_topics, pubsub_topic):
        """Ingests data from a kafka stream into big_query

        Args:
            kafka_config      (dict): Kafka consumer configuration properties
            bucket_name        (str): Name of the bucket to upload into
            kafka_topics (list[str]): Kafka topics to subscribe to
        """

        self.server = kafka_config["bootstrap.servers"]
        log.info(f'Instantiating consumer for {self.server}')

        # Enforce NO auto commit
        commit_config = kafka_config.get('enable.auto.commit', None)
        if commit_config != 'FALSE':
            warn(f'enable.auto.commit set to {commit_config} - changing to `False`')
            kafka_config.setdefault('enable.auto.commit', 'FALSE')

        # Connect to ZTF stream
        super().__init__(kafka_config)
        self.subscribe(kafka_topics)

        # Connect to Google Cloud
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.get_bucket(bucket_name)

        # Configure PubSub
        # The ``topic_path`` method creates a fully qualified identifier
        # in the form ``projects/{project_id}/topics/{topic_name}``
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
        with TemporaryFile() as temp_file:
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
                    # self.commit()

                break

        except KeyboardInterrupt:
            log.error('User ended consumer')
            raise

        except Exception as e:
            log.error(f'Consumer level error: {e}')
            raise
