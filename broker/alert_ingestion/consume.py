#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``consume`` module handles the ingestion of a Kafka alert stream into
Google Cloud Storage (GCS) and defines default connection settings for
different Kafka servers. If an alert's schema header needs to be corrected
to be compliant with BigQuery's strict validation standards, that change is
made here, before the alert is stored.

Usage Example
-------------

.. code-block:: python
   :linenos:

   from broker.alert_ingestion import consume

   # Define connection configuration using default values as a starting point
   config = consume.DEFAULT_ZTF_CONFIG.copy()
   config['sasl.kerberos.keytab'] = '<Path to authentication file>'
   config['sasl.kerberos.principal'] = '<Name of principal>'
   print(config)

   # Create a GCS consumer object
   c = consume.GCSKafkaConsumer(
       kafka_config=config,
       kafka_topic='my_kafka_topic_name',
       bucket_name='<PROJECT_ID>_ztf_alert_avro_bucket',
       pubsub_alert_data_topic='ztf_alert_data',
       pubsub_in_GCS_topic='ztf_alert_avro_in_bucket',
       debug=True  # Use debug to run without updating your kafka offset
   )

   # Ingest alerts one at a time indefinitely
   c.run()

Default Config Settings
-----------------------

Dictionaries with a subset of default configuration settings are provided as
described below.

+-----------------------------------------+-----------------------------------+
| Survey Name                             | Variable Name                     |
+=========================================+===================================+
| Zwicky Transient Facility               | `DEFAULT_ZTF_CONFIG`              |
+-----------------------------------------+-----------------------------------+

Module Documentation
--------------------
"""

import logging
import os
import re
from pathlib import Path
from tempfile import SpooledTemporaryFile
from warnings import warn
import pickle
import fastavro
from confluent_kafka import Consumer, KafkaException

from broker import exceptions
from broker.pub_sub_client.message_service import publish_pubsub

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
    """Subclass of SpooledTemporaryFile that is tied into the log

    Log warning is issued when file rolls over onto disk.
    """

    def rollover(self) -> None:
        """Move contents of the spooled file from memory onto disk"""

        log.warning(f'Alert size exceeded max memory size: {self._max_size}')
        super().rollover()

    @property
    def readable(self):
        return self._file.readable

    @property
    def writable(self):
        return self._file.writable

    @property
    def seekable(self):  # necessary so that fastavro can write to the file
        return self._file.seekable


def _set_config_defaults(kafka_config: dict) -> dict:
    """Set default values for a Kafka configuration dictionaryk

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
    """Ingests data from a kafka stream into BigQuery"""

    def __init__(
            self,
            kafka_config: dict,
            kafka_topic: str,
            bucket_name: str,
            pubsub_alert_data_topic: str,
            pubsub_in_GCS_topic: str,
            debug: bool = False):
        """Ingests data from a kafka stream and stores a copy in GCS

        Storage bucket and PubSub topics must already exist and have
        appropriate permissions.

        Args:
            kafka_config: Kafka consumer configuration properties
            kafka_topic: Kafka topics to subscribe to
            bucket_name: Name of the CGS bucket to upload into
            pubsub_alert_data_topic: PubSub topic for alert data
            pubsub_in_GCS_topic: PubSub topic for "alert in GCS" notifications
            debug: Run without committing Kafka position
        """

        self._debug = debug
        self.kafka_topic = kafka_topic
        self.bucket_name = bucket_name
        self.pubsub_alert_data_topic = pubsub_alert_data_topic
        self.pubsub_in_GCS_topic = pubsub_in_GCS_topic
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

    def close(self) -> None:
        """Close down and terminate the Kafka Consumer"""

        log.info(f'Closing consumer: {self.__repr__()}')
        super().close()

    @staticmethod
    def fix_schema(temp_file: TempAlertFile, survey: str, version: str) -> None:
        """ Rewrites the temp_file with a corrected schema header
            so that it is valid for upload to BigQuery.

        Args:
            temp_file: Temporary file containing the alert.
            survey: Name of the survey generating the alert.
            version: Schema version.
        """

        # get the corrected schema if it exists, else return
        try:
            fpkl = f'valid_schemas/{survey}_v{version}.pkl'
            inpath = Path(__file__).resolve().parent / fpkl
            with inpath.open('rb') as infile:
                valid_schema = pickle.load(infile)

        except FileNotFoundError:
            msg = f'Original schema header retained for {survey} v{version}'
            log.debug(msg)
            return

        # load the file and get the data with fastavro
        temp_file.seek(0)
        data = [r for r in fastavro.reader(temp_file)]

        # write the corrected file
        temp_file.seek(0)
        fastavro.writer(temp_file, valid_schema, data)
        temp_file.truncate()  # removes leftover data
        temp_file.seek(0)

        log.debug(f'Schema header reformatted for {survey} version {version}')

    def upload_bytes_to_bucket(self, data: bytes, destination_name: str) -> None:
        """Uploads bytes data to a GCP storage bucket. Prior to storage,
        corrects the schema header to be compliant with BigQuery's strict
        validation standards if the alert is from a survey version with an
        associated pickle file in the valid_schemas directory.

        Args:
            data: Data to upload
            destination_name: Name of the file to be created
        """

        log.debug(f'Uploading {destination_name} to {self.bucket.name}')
        blob = self.bucket.blob(destination_name)

        # Get the survey name and version
        survey = guess_schema_survey(data)
        version = guess_schema_version(data)

        # By default, spool data in memory to avoid IO unless data is too big
        # LSST alerts are anticipated at 80 kB, so 150 kB should be plenty
        max_alert_packet_size = 150000
        with TempAlertFile(max_size=max_alert_packet_size, mode='w+b') as temp_file:
            temp_file.write(data)
            temp_file.seek(0)
            self.fix_schema(temp_file, survey, version)
            blob.upload_from_file(temp_file)

    def run(self) -> None:
        """Ingest kafka Messages to GCS and PubSub"""

        log.info('Starting consumer.run ...')
        try:
            while True:
                msg = self.consume(num_messages=1, timeout=1)
                # print(msg)
                if msg is None:
                    log.warn('msg is None')
                    continue

                # msg = msg[0]

                if msg.error():
                    err_data = (msg.topic(), msg.partition(), msg.offset(), msg.key(), msg.error())
                    err_msg = 'KafkaException for {} [{}] at offset {} with key {}:\n  %%  {}'.format(*err_data)
                    log.error(err_msg, exc_info=True)
                    raise KafkaException(msg.error())

                else:
                    timestamp_kind, timestamp = msg.timestamp()
                    file_name = f'{timestamp}.avro'

                    log.debug(f'Ingesting {file_name}')
                    publish_pubsub(self.pubsub_in_GCS_topic, file_name.encode('UTF-8'))
                    publish_pubsub(self.pubsub_alert_data_topic, msg.value())
                    self.upload_bytes_to_bucket(msg.value(), file_name)

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
            f'pubsub_alert_data_topic: {self.pubsub_alert_data_topic}'
            f'pubsub_in_GCS_topic: {self.pubsub_in_GCS_topic}'
            ')>'
        )


def guess_schema_version(alert_bytes: bytes) -> str:
    """Retrieve the ZTF schema version

    Args:
        alert_bytes: An alert from ZTF or LSST

    Returns:
        The schema version
    """

    version_regex_pattern = b'("version":\s")([0-9]*\.[0-9]*)(")'
    version_match = re.search(version_regex_pattern, alert_bytes)
    if version_match is None:
        err_msg = f'Could not guess schema version for alert {alert_bytes}'
        log.error(err_msg)
        raise exceptions.SchemaParsingError(err_msg)

    return version_match.group(2).decode()

def guess_schema_survey(alert_bytes: bytes) -> str:
    """Retrieve the ZTF schema version

    Args:
        alert_bytes: An alert from ZTF or LSST

    Returns:
        The survey name
    """

    survey_regex_pattern = b'("namespace":\s")(\S*)(")'
    survey_match = re.search(survey_regex_pattern, alert_bytes)
    if survey_match is None:
        err_msg = f'Could not guess survey name for alert {alert_bytes}'
        log.error(err_msg)
        raise exceptions.SchemaParsingError(err_msg)

    return survey_match.group(2).decode()
