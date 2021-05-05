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

from broker_utils import beam_transforms as bbt
from broker_utils import schema_maps as bsm


def load_schema_map(SURVEY, TESTID):
    # load the schema map from the broker bucket in Cloud Storage
    return bsm.load_schema_map(SURVEY, TESTID)

def sink_configs(PROJECTID):
    """Configuration dicts for all pipeline sinks.

    Args:
        PROJECTID (str): Google Cloud Platform project ID

    Returns:
        sink_configs = {'sinktype_dataDescription': {'config_name': value, }, }
    """
    sink_configs = {
            'BQ_generic': {
                'project': PROJECTID,
                'create_disposition': bqdisp.CREATE_NEVER,
                'write_disposition': bqdisp.WRITE_APPEND,
                'validate': False,
                'insert_retry_strategy': RetryStrategy.RETRY_ON_TRANSIENT_ERROR,
            },
            'PS_generic': {
                'with_attributes': False,  # currently using bytes
                #  may want to use these in the future:
                'id_label': None,
                'timestamp_attribute': None
            },
    }

    return sink_configs

def run(schema_map, sources, sinks, sink_configs, pipeline_args):
    """Runs the Alerts -> BigQuery pipeline.
    """
    pipeline_options = PipelineOptions(pipeline_args, streaming=True)

    with beam.Pipeline(options=pipeline_options) as pipeline:

        #-- Read from PS and extract data as dicts
        alert_bytes = (
            pipeline | 'ReadFromPubSub' >>
            ReadFromPubSub(topic=sources['PS_alerts'])
        )
        full_alert_dicts = (
            alert_bytes | 'ExtractAlertDict' >>
            beam.ParDo(bbt.ExtractAlertDict())
        )
        alert_dicts = (
            full_alert_dicts | 'StripCutouts' >>
            beam.ParDo(bbt.StripCutouts(schema_map))
        )

        #-- Upload original alert data to BQ
        adicts_deadletters = (
            alert_dicts | 'Write Alert BigQuery' >>
            WriteToBigQuery(sinks['BQ_alerts'], **sink_configs['BQ_generic'])
        )  # TODO: track deadletters, get them uploaded to bq

        #-- Extract the DIA source info and upload to BQ
        dias_dicts = (
            alert_dicts | 'extractDIASource' >>
            beam.ParDo(bbt.ExtractDIASource(schema_map))
        )
        ddicts_deadletters = (
            dias_dicts | 'Write DIASource BigQuery' >>
            WriteToBigQuery(sinks['BQ_diasource'], **sink_configs['BQ_generic'])
        )  # TODO: track deadletters, get them uploaded to bq


if __name__ == "__main__":  # noqa
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--PROJECTID",
        help="Google Cloud Platform project name.\n",
    )
    parser.add_argument(
        "--SURVEY",
        help="Survey this broker instance is associated with.\n",
    )
    parser.add_argument(
        "--TESTID",
        help="testid this broker instance is associated with.\n",
    )
    parser.add_argument(
        "--source_PS_alerts",
        help="Pub/Sub topic to read alerts from.\n"
        '"projects/<PROJECT_NAME>/topics/<TOPIC_NAME>".',
    )
    parser.add_argument(
        "--sink_BQ_alerts",
        help="BigQuery table to store original alert data.\n",
    )
    parser.add_argument(
        "--sink_BQ_diasource",
        help="BigQuery table to store DIA source data.\n",
    )

    known_args, pipeline_args = parser.parse_known_args()

    schema_map = load_schema_map(known_args.SURVEY, known_args.TESTID)
    sources = {'PS_alerts': known_args.source_PS_alerts}
    sinks = {
            'BQ_alerts': known_args.sink_BQ_alerts,
            'BQ_diasource': known_args.sink_BQ_diasource,
    }
    sink_configs = sink_configs(known_args.PROJECTID)

    run(schema_map, sources, sinks, sink_configs, pipeline_args)
