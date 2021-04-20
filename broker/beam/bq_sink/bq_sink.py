#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``bq_sink`` runs a Beam pipeline to dump alert data to BigQuery.

Module Documentation
--------------------
"""

import argparse
import logging
import apache_beam as beam
from apache_beam.io import BigQueryDisposition as bqdisp
from apache_beam.io import ReadFromPubSub, WriteToPubSub, WriteToBigQuery
from apache_beam.io.gcp.bigquery_tools import RetryStrategy
from apache_beam.options.pipeline_options import PipelineOptions

from beam_helpers import data_utils as dutil


def sink_configs(PROJECTID):
    """Configuration dicts for all pipeline sinks.

    Args:
        PROJECTID (str): Google Cloud Platform project ID

    Returns:
        snkconf = {'sinktype_dataDescription': {'config_name': value, }, }
    """
    snkconf = {
            'BQ_generic': {
                # 'schema': 'SCHEMA_AUTODETECT',
                'project': PROJECTID,
                'create_disposition': bqdisp.CREATE_NEVER,
                'write_disposition': bqdisp.WRITE_APPEND,
                'validate': False,
                'insert_retry_strategy': RetryStrategy.RETRY_ON_TRANSIENT_ERROR,
                # 'batch_size': 5000,
            },
            'PS_generic': {
                'with_attributes': False,  # currently using bytes
                #  may want to use these in the future:
                'id_label': None,
                'timestamp_attribute': None
            },
    }

    return snkconf

def run(PROJECTID, sources, sinks, pipeline_args):
    """Runs the ZTF -> BigQuery pipeline.
    """

    pipeline_options = PipelineOptions(pipeline_args, streaming=True)
    snkconf = sink_configs(PROJECTID)

    with beam.Pipeline(options=pipeline_options) as pipeline:

        #-- Read from PS and extract data as dicts
        alert_bytes = (
            pipeline | 'ReadFromPubSub' >>
            ReadFromPubSub(topic=sources['PS_ztf'])
        )
        full_alert_dicts = (
            alert_bytes | 'ExtractAlertDict' >>
            beam.ParDo(dutil.extractAlertDict())
        )
        alert_dicts = (
            full_alert_dicts | 'StripCutouts' >>
            beam.ParDo(dutil.stripCutouts())
        )

        #-- Upload original alert data to BQ
        # BQ encoding error until cutouts were stripped. see StripCutouts() for more details
        # alerts with no history cannot currently be uploaded -> RETRY_NEVER
        # TODO: track deadletters, get them uploaded to bq
        adicts_deadletters = (
            alert_dicts | 'Write Alert BigQuery' >>
            WriteToBigQuery(sinks['BQ_originalAlert'],
                **snkconf['BQ_generic'])
        )

        #-- Extract the DIA source info and upload to BQ
        dias_dicts = (
            alert_dicts | 'extractDIASource' >>
            beam.ParDo(dutil.extractDIASource())
        )
        ddicts_deadletters = (
            dias_dicts | 'Write DIASource BigQuery' >>
            WriteToBigQuery(sinks['BQ_diasource'],
                **snkconf['BQ_generic'])
        )


if __name__ == "__main__":  # noqa
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--PROJECTID",
        help="Google Cloud Platform project name.\n",
    )
    parser.add_argument(
        "--source_PS_ztf",
        help="Pub/Sub topic to read alerts from.\n"
        '"projects/<PROJECT_NAME>/topics/<TOPIC_NAME>".',
    )
    parser.add_argument(
        "--sink_BQ_originalAlert",
        help="BigQuery table to store original alert data.\n",
    )
    parser.add_argument(
        "--sink_BQ_diasource",
        help="BigQuery table to store DIA source data.\n",
    )

    known_args, pipeline_args = parser.parse_known_args()

    sources = {'PS_ztf': known_args.source_PS_ztf}
    sinks = {
            'BQ_originalAlert': known_args.sink_BQ_originalAlert,
            'BQ_diasource': known_args.sink_BQ_diasource,
    }

    run(known_args.PROJECTID, sources, sinks, pipeline_args)
