#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""Ingest alerts from a Kafka stream to GCS Storage and PubSub"""

import os
from warnings import warn

from confluent_kafka import Consumer, KafkaException
from google.cloud import pubsub_v1, storage

from .utils import RTDSafeImport, setup_log

with RTDSafeImport():
    error_client, log = setup_log(__name__)

DEFAULT_ZTF_CONFIG = {
    'bootstrap.servers': 'public2.alerts.ztf.uw.edu:9094',
    'group.id': 'group',
    'session.timeout.ms': 6000,
    'enable.auto.commit': 'FALSE',
    'sasl.kerberos.principal': 'pitt-reader@KAFKA.SECURE',
    'sasl.kerberos.kinit.cmd': 'kinit -t "%{sasl.kerberos.keytab}" -k %{sasl.kerberos.principal}',
    'sasl.kerberos.keytab': None,
    'sasl.kerberos.service.name': 'kafka',
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.mechanisms': 'GSSAPI',
    'auto.offset.reset': 'earliest'
}


class GCSKafkaConsumer(Consumer):
    """Ingests data from a kafka stream into big_query"""

    def __init__(self, config, bucket_name, kafka_topics, pubsub_topic):
        """Ingests data from a kafka stream into big_query

        Args:
            config      (dict): Kafka consumer configuration properties
            bucket_name  (str): Name of the bucket to upload into
            kafka_topics (list[str]): Kafka topics to subscribe to
        """

        # Enforce NO auto commit
        commit_config = config.get('enable.auto.commit', None)
        if commit_config != 'FALSE':
            warn(f'enable.auto.commit set to {commit_config} - changing to `False`')
            config.setdefault('enable.auto.commit', 'FALSE')

        # Connect to ZTF stream
        super().__init__(config)
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

    def upload_to_bucket(self, file_obj, destination_name):
        """Uploads a file like object to a GCP storage bucket

        Args:
            file_obj    (BinaryIO): Name of the bucket to upload into
            destination_name (str): Name of the file to be created
        """

        blob = self.bucket.blob(destination_name)
        blob.upload_from_filename(file_obj)

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

        while True:
            msg = self.poll()

            if msg is None:
                continue

            if msg.error():
                err_msg = '{} [{}] at offset {} with key {}:\n  %%  {}'
                err_data = (msg.topic(), msg.partition(), msg.offset(), msg.key(), msg.error())
                log.log(err_msg.format(err_data))
                raise KafkaException(msg.error())

            else:
                # Todo: Is msg.key() unique? How to name GCS Files
                file_name = msg.key()
                self.upload_to_bucket(msg.value(), msg.key())
                self.publish_pubsub(file_name)
                self.commit()
