#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``salt2_utils`` module contains classes and functions to
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


class FormatForSalt2(DoFn):
    """ Prepares an alert dict for a Salt2 fit.
    Extracts epoch data and calculates some statistics.
    """
    def __init__(self, salt2_configs):
        super().__init__()
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

        # extract epoch data
        epoch_dict = self.extract_epochs(alert)

        # format epoch data for salt2 and extract some stats
        # epochInfo = {'epochTable': <Table>, 'epochStats': <dict>}
        epochInfo = self.format_for_salt2(epoch_dict)

        # add some metadata
        epochInfo['objectId'] = alert['objectId']
        epochInfo['candid'] = alert['candid']

        return [epochInfo]

    def extract_epochs(self, alert):
        """ Collects data from each observation epoch of a single alert.

        Args:
            alert (dict): dictionary of alert data from ZTF

        Returns:
            epoch_dict (dict): keys: 'mjd','flux','fluxerr','passband'
                            values: Lists of light curve data with one element
                                    per epoch.
        """

        # collect epochs
        epochs = alert['prv_candidates'] + [alert['candidate']]

        # prepare empty lists to zip epoch data
        mjd, flux, fluxerr, passband, magzpsci, magzpsciunc, zpsys, isdiffpos = ([] for i in range(8))
        # bandpass mapping
        fid_dict = {1: 'g', 2: 'r', 3: 'i'}

        for n, epoch in enumerate(epochs):
            # skip nondetections.
            if epoch['magpsf'] is None: continue
            # in the future, may want to set this to epoch['diffmaglim']

            # Gather epoch data
            mjd.append(self.jd_to_mjd(epoch['jd']))
            f, ferr = self.mag_to_flux(epoch['magpsf'], epoch['magzpsci'],
                                       epoch['sigmapsf'])
            flux.append(f)
            fluxerr.append(ferr)
            passband.append(fid_dict[epoch['fid']])
            magzpsci.append(epoch['magzpsci'])
            magzpsciunc.append(epoch['magzpsciunc'])
            zpsys.append('ab')
            isdiffpos.append(epoch['isdiffpos']) # used to count detections/nondetections (null if non)

        # Gather info
        epoch_dict = {
            'mjd': np.asarray(mjd),
            'flux': np.asarray(flux),
            'fluxerr': np.asarray(fluxerr),
            'passband': np.asarray(passband),
            'magzpsci': magzpsci,
            'magzpsciunc': magzpsciunc,
            'zpsys': zpsys,
            'isdiffpos': np.asarray(isdiffpos)
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

        col_map = {# salt2_name: ztf_name,
                    'time': 'mjd',
                    'band': 'passband',
                    'flux': 'flux',
                    'fluxerr': 'fluxerr',
                    'zp': 'magzpsci',
                    'zpsys': 'zpsys',
                    }

        data = {sname: epoch_dict[zname] for sname, zname in col_map.items()}
        # convert bandpass to name registered in sncosmo
        data['band'] = [f'ztf{val}' for val in data['band']]

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

        num_detections = np.sum(epoch_dict['isdiffpos'] == 't')
        # this is how ZTF counts detections in their is_transient() filter

        epochStats = {
                    'maxSN': maxSN,
                    't0_guess': t0_guess,
                    'num_detections': num_detections,
                }

        return epochStats

    def mag_to_flux(self, mag, zeropoint, magerr):
        """ Converts an AB magnitude and its error to fluxes.
        """
        flux = 10 ** ((zeropoint - mag) / 2.5)
        fluxerr = flux * magerr * np.log(10 / 2.5)
        return flux, fluxerr

    def jd_to_mjd(self, jd):
        """ Converts Julian Date to modified Julian Date.
        """
        return Time(jd, format='jd').mjd


def salt2_quality_cuts(epochInfo, salt2_configs):
    """ Filter to enforce minimum data quality before fitting with Salt2.

    Example Usage:
        epochInfoDicts | beam.Filter(salt2_quality_cuts, salt2_configs)

    Args:
        epochInfo (dict): element of the PCollection returned by `beam.ParDo(FormatForSalt2())`
        salt2_configs (dict): should contain:
            salt2_configs['SNthresh'] (float): min S/N necessary to fit with Salt2
            salt2_configs['minNdetections'] (int): min number of detections necessary to fit with Salt2

    Returns:
        min_quality (bool): whether the epochs pass minimum data quality requirements.
    """

    epochStats = epochInfo['epochStats']
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
    def process(self, epochInfo):
        """ Performs a Salt2 fit on alert history.

        Args:
            epochInfo (dict): element of the PCollection returned by `beam.ParDo(FormatForSalt2())`

        Yields:
            salt2FitResult (dict): output of Salt2 fit, formatted for BigQuery and Pub/Sub
            salt2Fit4Figure (dict): data, model, and result; needed to do sncosmo.plot_lc()
        """
        objectId = epochInfo['objectId']
        candid = epochInfo['candid']
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
            logging.info(f'Salt2 fit failed with DataQualityError for alertID {candid}. {dqe}')

        else:
            # yield salt2FitResult formatted for BQ and PS to the main output
            # cov_names depreciated in favor of vparam_names, but flatten_result() requires it
            result['cov_names'] = result['vparam_names']
            flatresult = dict(sncosmo.flatten_result(result))
            yield {'objectId': objectId, 'candid': candid, **flatresult,}

            # yield info needed to plot lightcurve to a tagged output
            salt2Fit4Figure = {
                    'objectId': objectId,
                    'candid': candid,
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

    def start_bundle(self):
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
        candid = salt2Fit4Figure['candid']
        epochTable = salt2Fit4Figure['epochTable']
        result = salt2Fit4Figure['result']
        fitted_model = salt2Fit4Figure['fitted_model']

        # plot the lightcurve and save in bucket
        with NamedTemporaryFile(suffix=".png") as temp_file:
                fig = sncosmo.plot_lc(epochTable, model=fitted_model, errors=result.errors)
                fig.savefig(temp_file, format="png")
                temp_file.seek(0)
                # upload to GCS
                gcs_filename = f'candid_{candid}.png'
                blob = self.bucket.blob(f'salt2/plot_lc/{gcs_filename}')
                blob.upload_from_filename(filename=temp_file.name)

        return None
