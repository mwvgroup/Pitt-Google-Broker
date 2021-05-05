#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``salt2`` module contains classes and functions to
perform a Salt2 fit on the lightcurve of a ZTF alert
and store the results.

Usage Example
-------------

.. code-block:: python
   :linenos:

    # The Beam pipeline can contain the following `ParDo` transform:
    salt2Dicts = (adscExgalTrans | 'fitSalt2' >> beam.ParDo(fitSalt2()))
    # where `adscExgalTrans` is an alert dict stripped of the cutouts
    # and passed through the `is_extragalactic_transient` filter.

Module Documentation
--------------------
"""

from base64 import b64encode
import logging
from tempfile import NamedTemporaryFile
import numpy as np
from apache_beam import DoFn
from apache_beam import pvalue
from astropy.table import Table
from astropy.time import Time
import sncosmo
from sncosmo.fitting import DataQualityError
from google.cloud import storage

from broker_utils import data_utils as bdu


class FormatForSalt2(DoFn):
    """ Prepares an alert dict for a Salt2 fit.
    Extracts epoch data and calculates some statistics.
    """
    def __init__(self, schema_map, salt2_configs):
        super().__init__()
        self.schema_map = schema_map
        self.salt2_configs = salt2_configs

    def process(self, alert):
        """
        Args:
            alert (dict): dictionary of alert data from ZTF

        Returns:
            epochInfo (dict): contains:
                epochTable (Table): epoch data formatted as Astropy Table
                epochStats (dict): get_epoch_stats(epoch_dict)
                objectId (str): alert['objectId']
                candid (int): alert['candid']
        """
        schema_map = self.schema_map

        # extract epoch data
        epoch_dict = self.extract_epochs(alert)

        # format epoch data for salt2 and extract some stats
        # epochInfo = {'epochTable': <Table>, 'epochStats': <dict>}
        epochInfo = self.format_for_salt2(epoch_dict)

        # add some metadata
        epochInfo['objectId'] = alert[schema_map['objectId']]
        epochInfo['sourceId'] = alert[schema_map['sourceId']]

        # package with the alert so Pub/Sub can have both
        alert_epoch_dicts = {'alert': alert, 'epochInfo': epochInfo}

        return [alert_epoch_dicts]

    def extract_epochs(self, alert):
        """ Collects data from each observation epoch of a single alert.

        Args:
            alert (dict): dictionary of alert data from ZTF

        Returns:
            epoch_dict (dict): keys: 'mjd','flux','fluxerr','passband'
                            values: Lists of light curve data with one element
                                    per epoch.
        """
        schema_map = self.schema_map
        survey = schema_map['SURVEY']
        filter_map = schema_map['FILTER_MAP']  # bandpass mapping

        # collect epochs
        epochs = alert[schema_map['prvSources']] + [alert[schema_map['source']]]

        # prepare empty lists to zip epoch data
        mjd, flux, fluxerr, passband = ([] for i in range(4))
        magzp, magzpunc, zpsys, isdetection = ([] for i in range(4))

        for n, epoch in enumerate(epochs):
            # skip if no magnitude included
            if epoch[schema_map['mag']] is None: continue

            # Gather epoch data
            if survey == 'decat':
                mjdate = epoch['mjd']
                f, ferr = epoch['flux'], epoch['fluxerr']
                mzpunc = None
                isdetect = (epoch[schema_map['mag']] is not None)

            elif survey == 'ztf':
                mjdate = bdu.jd_to_mjd(epoch['jd'])
                f, ferr = bdu.mag_to_flux(epoch['magpsf'],
                                           epoch['magzpsci'],
                                           epoch['sigmapsf'])
                mzpunc = epoch['magzpsciunc']
                isdetect = epoch['isdiffpos'] == 't'
                # this is how ZTF counts detections in their is_transient() filter

            mjd.append(mjdate)
            flux.append(f)
            fluxerr.append(ferr)
            passband.append(filter_map[epoch[schema_map['filter']]])
            magzp.append(epoch[schema_map['magzp']])
            magzpunc.append(mzpunc)
            zpsys.append('ab')
            isdetection.append(isdetect)

        # Gather info
        epoch_dict = {
            'mjd': np.asarray(mjd),
            'flux': np.asarray(flux),
            'fluxerr': np.asarray(fluxerr),
            'passband': np.asarray(passband),
            'magzp': np.asarray(magzp),
            'magzpunc': np.asarray(magzpunc),
            'zpsys': np.asarray(zpsys),
            'isdetection': np.asarray(isdetection)
        }

        return epoch_dict

    def format_for_salt2(self, epoch_dict):
        """ Formats alert data for input to Salt2.
        Extracts some statistics

        Args:
            epoch_dict (dict): epoch_dict = extract_epochs(alert)

        Returns:
            epochInfo (dict): contains:
                epochTable (Table): epoch data formatted as Astropy Table
                epochStats (dict): get_epoch_stats(epoch_dict)
        """
        schema_map = self.schema_map
        col_map = { # salt2_name: name_used_by_broker,
                    'time': 'mjd',
                    'band': 'passband',
                    'flux': 'flux',
                    'fluxerr': 'fluxerr',
                    'zp': 'magzp',
                    'zpsys': 'zpsys',
                    }
        data = {s2name: epoch_dict[bname] for s2name, bname in col_map.items()}

        # convert bandpass to name registered in sncosmo
        if schema_map['SURVEY'] == 'decat':
            prefix = 'sdss'
        elif schema_map['SURVEY'] == 'ztf':
            prefix = 'ztf'
        data['band'] = [f'{prefix}{val}' for val in data['band']]

        epochInfo = {
                    'epochTable': Table(data),
                    'epochStats': self.get_epoch_stats(epoch_dict),
        }

        return epochInfo

    def get_epoch_stats(self, epoch_dict):
        """ Returns statistics used in quality cuts and Salt2 fit.

        Args:
            epoch_dict (dict): epoch_dict = extract_epochs(alert)

        Also uses:
            self.salt2_configs['SNthresh'] (float): S/N threshold.
            Salt2 param t0 constrained around first epoch with S/N > SNthresh.

        Returns:
            epochStats (dict): contains maxSN, t0_guess, num_detections
        """

        SNthresh = self.salt2_configs['SNthresh']
        SN = epoch_dict['flux'] / epoch_dict['fluxerr']
        maxSN = np.max(SN)

        # to constrain t0, find mjd of first epoch with S/N > SNthresh
        if maxSN > SNthresh:
            first_SN_above_thresh = np.where(SN>SNthresh)[0][0]
            t0_guess = epoch_dict['mjd'][first_SN_above_thresh]
        else:
            t0_guess = None

        num_detections = np.sum(epoch_dict['isdetection'])

        epochStats = {
                    'maxSN': maxSN,
                    't0_guess': t0_guess,
                    'num_detections': num_detections,
                }

        return epochStats


def salt2_quality_cuts(alert_epoch_dicts, salt2_configs):
    """ Filter to enforce minimum data quality before fitting with Salt2.

    Args:
        alert_epoch_dicts ({dict},{dict}): element of the PCollection returned by `beam.ParDo(FormatForSalt2())`
        salt2_configs (dict): should contain:
            salt2_configs['SNthresh'] (float): min S/N necessary to fit with Salt2
            salt2_configs['minNdetections'] (int): min number of detections necessary to fit with Salt2

    Returns:
        min_quality (bool): whether the epochs pass minimum data quality requirements.
    """
    epochStats = alert_epoch_dicts['epochInfo']['epochStats']
    SNthresh = salt2_configs['SNthresh']
    minNdetections = salt2_configs['minNdetections']

    has_min_SN = epochStats['maxSN'] >= SNthresh
    has_min_Ndetections = epochStats['num_detections'] >= minNdetections

    return has_min_SN and has_min_Ndetections


class FitSalt2(DoFn):
    """ Performs a Salt2 fit on alert history.

    Example usage:
        epochInfoDicts | beam.ParDo(FitSalt2())
    """
    def __init__(self, schema_map):
        super().__init__()
        self.schema_map = schema_map

    def process(self, alert_epoch_dicts):
        """ Performs a Salt2 fit on alert history.

        Args:
            alert_epoch_dicts ({dict,dict}): element of the PCollection returned by `beam.ParDo(FormatForSalt2())`

        Yields:
            salt2Fit (dict): output of Salt2 fit, formatted for BigQuery and Pub/Sub
            salt2Fit4Figure (dict): data, model, and result; needed to do sncosmo.plot_lc()
        """
        schema_map = self.schema_map

        # unpack the data
        alert, epochInfo = alert_epoch_dicts['alert'], alert_epoch_dicts['epochInfo']
        objectId = epochInfo['objectId']
        sourceId = epochInfo['sourceId']
        epochTable = epochInfo['epochTable']
        epochStats = epochInfo['epochStats']

        # fit with salt2
        t0_guess, t0_pm = int(epochStats['t0_guess']), 10
        model = sncosmo.Model(source='salt2')
        try:
            result, fitted_model = sncosmo.fit_lc(epochTable, model,
                                    ['z', 't0', 'x0', 'x1', 'c'],  # parameters of model to vary
                                    bounds={'z': (0.01, 0.2),  # https://arxiv.org/pdf/2009.01242.pdf
                                            'x1': (-5.,5.),
                                            'c': (-5.,5.),
                                            't0': (t0_guess-t0_pm,t0_guess+t0_pm),
                                    }
            )

        # if DataQualityError, log the error and yield nothing
        except DataQualityError as dqe:
            msg = f'Salt2 fit failed for objectId {objectId}, sourceId {sourceId}. {dqe}'
            logging.info(msg)

        # yield results
        else:
            # yield salt2Fit formatted for BQ to the main output
            # cov_names depreciated in favor of vparam_names, but flatten_result() requires it
            result['cov_names'] = result['vparam_names']
            flatresult = dict(sncosmo.flatten_result(result))
            salt2Fit = {  # name fields to match BigQuery schema
                schema_map['objectId']: objectId,
                schema_map['sourceId']: sourceId,
                **flatresult,
            }
            yield salt2Fit

            # yield alert + salt2Fit for PS, to a tagged output
            alert_salt2Fit = {'alert': alert, 'salt2Fit': salt2Fit}
            yield pvalue.TaggedOutput('alert_salt2Fit', alert_salt2Fit)

            # yield info needed to plot lightcurve to a tagged output
            salt2Fit4Figure = {
                    'objectId': objectId,
                    'sourceId': sourceId,
                    'epochTable': epochTable,
                    'result': result,
                    'fitted_model': fitted_model,
                    }
            yield pvalue.TaggedOutput('salt2Fit4Figure', salt2Fit4Figure)


class StoreSalt2FitFigure(DoFn):
    """ Creates and stores (in GCS) a figure of the alert lightcurves and Salt2 fits.

    Example usage:
        salt2Fit4Figure | beam.ParDo(StoreSalt2FitFigure(sinks['CS_salt2']))

    """
    def __init__(self, sink_CS_salt2):
        super().__init__()
        self.sink_CS_salt2 = sink_CS_salt2  # bucket name to store the figure

    def setup(self):
        # Connect to Google Cloud Storage to store lc+fit figures
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.sink_CS_salt2)

    def process(self, salt2Fit4Figure):
        """ Create and store the figure

        Args:
            salt2Fit4Figure (dict): element of the PCollection tagged "salt2Fit4Figure" returned by `beam.ParDo(FitSalt2())`
        """
        # unpack the input dict
        objectId = salt2Fit4Figure['objectId']
        sourceId = salt2Fit4Figure['sourceId']
        epochTable = salt2Fit4Figure['epochTable']
        result = salt2Fit4Figure['result']
        fitted_model = salt2Fit4Figure['fitted_model']

        # plot the lightcurve and save in bucket
        with NamedTemporaryFile(suffix=".png") as temp_file:
                fig = sncosmo.plot_lc(epochTable, model=fitted_model, errors=result.errors)
                fig.savefig(temp_file, format="png")
                temp_file.seek(0)
                # upload to GCS
                gcs_filename = f'{objectId}.{sourceId}.png'
                blob = self.bucket.blob(f'salt2/plot_lc/{gcs_filename}')
                blob.upload_from_filename(filename=temp_file.name)

        return None
