#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``fit_salt2`` module attempts to perform a Salt2 fit on a
ZTF alert dictionary. If successful, a figure (lightcurve + Salt2 fit)
is stored to Cloud Storage, and the fit results are returned as a dict.

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
# import pandas as pd
from astropy.table import Table
from astropy.time import Time
# import astropy.units as u
import sncosmo
from sncosmo.fitting import DataQualityError
from apache_beam import DoFn
from google.cloud import storage


class fitSalt2(DoFn):
    """ Performs a Salt2 fit on alert history.

    Example usage:
        Beam Alert Packet PCollection | 'Salt2 fit' >> apache_beam.ParDo(beam_helpers.salt2fit())
    """
    def start_bundle(self, bucket_name='ardent-cycling-243415_ztf-sncosmo'):
        # Connect to Google Cloud Storage to store lc+fit figures
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(bucket_name)

    def process(self, alert):
        """ Performs a Salt2 fit on alert history.

        Args:
            alert (dict): dictionary of alert data from ZTF

        Returns:
            salt2_fit (dict): output of Salt2 fit, formatted for upload to BQ
        """

        SNthresh = 5.  # min S/N to proceed with fit, needed to get good amplitude fit
        num_det_thresh = 5  # min num detections to proceed with fit
        # move this ^ to a filter outside this function
        objectId = alert['objectId']
        candid = alert['candid']

        # extract epochs from alert
        epoch_dict = self.extract_epochs(alert)
        # format epoch data for salt2
        epoch_tbl, astats = self.format_for_salt2(epoch_dict)

        # return None if poor S/N
        if astats['maxSN'] < SNthresh:
            logging.info(f"max(S/N) = {astats['maxSN']} (< {SNthresh}) for alertID {candid}. \
                           Skipping Salt2 fit.")
            return None
        # return None if insuficient number of detections
        if astats['num_detections'] < num_det_thresh:
            logging.info(f"Number of detections = {astats['num_detections']} (< {num_det_thresh}) \
                           for alertID {candid}. Skipping Salt2 fit.")
            return None

        # fit with salt2
        t0_guess, t0_pm = int(astats['mjd_SNabove5']), 10
        model = sncosmo.Model(source='salt2')
        try:
            result, fitted_model = sncosmo.fit_lc(epoch_tbl, model,
                                    ['z', 't0', 'x0', 'x1', 'c'],  # parameters of model to vary
                                    bounds={'z': (0.01, 0.2),  # https://arxiv.org/pdf/2009.01242.pdf
                                            'x1': (-5.,5.),
                                            'c': (-5.,5.),
                                            't0': (t0_guess-t0_pm,t0_guess+t0_pm),
                                    }
            )

        # return None if there was an error
        except DataQualityError as dqe:
            logging.info(f'Salt2 fit failed with DataQualityError for alertID {candid}. {dqe}')
            return None
        # except RuntimeError as rte:
        #     logging.info(f'Salt2 fit failed with RuntimeError for alertID {candid}. {rte}')
        #     return None

        else:
            # cov_names depreciated in favor of vparam_names, but flatten_result() requires it
            result['cov_names'] = result['vparam_names']
            flatresult = dict(sncosmo.flatten_result(result))

            # filename = f'{candid}.png'
            # lfs.create(f'plotlc_temp/{filename}')

            # plot the lightcurve and save in bucket
            with NamedTemporaryFile(suffix=".png") as temp_file:
                    fig = sncosmo.plot_lc(epoch_tbl, model=fitted_model, errors=result.errors)
                    fig.savefig(temp_file, format="png")
                    temp_file.seek(0)
                    # upload to GCS
                    gcs_filename = f'candid_{candid}.png'
                    blob = self.bucket.blob(f'salt2/plot_lc/{gcs_filename}')
                    blob.upload_from_filename(filename=temp_file.name)
                    # bytestring for BQ
                    temp_file.seek(0)
                    # plot_lc_bytes = b64encode(temp_file.read())
                    # PS can't encode these bytes, drop them from the result dict

        return [{'objectId': objectId,
                 'candid': candid,
                 **flatresult,
                #  'plot_lc_bytes': plot_lc_bytes,
                }]

    def extract_epochs(self, alert):
        """ Collects data from each observation epoch of a single alert.

        Args:
            alert (dict): dictionary of alert data from ZTF

        Returns:
            epoch_dict (dict): keys: 'mjd','flux','fluxerr','passband','photflag'
                            values: Lists of light curve data with one element
                                    per epoch.
        """

        # collect epochs
        epochs = alert['prv_candidates'] + [alert['candidate']]

        # prepare empty lists to zip epoch data
        mjd, flux, fluxerr, passband, photflag, magzpsci, magzpsciunc, zpsys, isdiffpos = ([] for i in range(9))
        # passband mapping
        fid_dict = {1: 'g', 2: 'r', 3: 'i'}
        # set and track epochs with missing zeropoints
        zp_fallback, zp_in_keys = 26.0, [0 for i in range(len(epochs))]

        for n, epoch in enumerate(epochs):
            # skip nondetections.
            if epoch['magpsf'] is None: continue
            # fix this. try setting magnitude to epoch['diffmaglim']

            # check zeropoint (early schema(s) did not contain this)
            if 'magzpsci' not in epoch.keys():  # TODO: do something better.
                logging.warn('Epoch does not have zeropoint data. '
                    'Setting to {}'.format(zp_fallback))
                zp_in_keys[n] = 1
                epoch['magzpsci'] = zp_fallback

            # Gather epoch data
            mjd.append(self.jd_to_mjd(epoch['jd']))
            f, ferr = self.mag_to_flux(epoch['magpsf'], epoch['magzpsci'],
                                epoch['sigmapsf'])
            flux.append(f)
            fluxerr.append(ferr)
            passband.append(fid_dict[epoch['fid']])
            photflag.append(4096)  # fix this, determines trigger time
            # (1st mjd where this == 6144)
            magzpsci.append(epoch['magzpsci'])
            magzpsciunc.append(epoch['magzpsciunc'])
            zpsys.append('ab')
            isdiffpos.append(epoch['isdiffpos']) # used to count detections/nondetections (null if non)

        # # check zeropoint consistency for Rapid
        # # either 0 or all epochs (with detections) should be missing zeropoints
        # if sum(zp_in_keys) not in [0, len(mjd)]:
        #     raise ValueError((f'Inconsistent zeropoint values in alert {oid}. '
        #                     'Cannot continue with classification.'))

        # # Set trigger date for Rapid. fix this.
        # photflag = np.asarray(photflag)
        # photflag[flux == np.max(flux)] = 6144

        # Gather info
        epoch_dict = {
            'mjd': np.asarray(mjd),
            'flux': np.asarray(flux),
            'fluxerr': np.asarray(fluxerr),
            'passband': np.asarray(passband),
            # 'photflag': photflag,
            'magzpsci': magzpsci,
            'magzpsciunc': magzpsciunc,
            'zpsys': zpsys,
            'isdiffpos': np.asarray(isdiffpos)
        }

        return epoch_dict

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

    def format_for_salt2(self, epoch_dict):
        """ Formats alert data for input to Salt2.

        Args:
            epoch_dict (dict): epoch_dict = extract_epochs(epochs)

        Returns:
            epoch_tbl: (Table): astropy Table of epoch data formatted for Salt2
        """

        col_map = {# salt2 name: ztf name,
                    'time': 'mjd',
                    'band': 'passband',
                    'flux': 'flux',
                    'fluxerr': 'fluxerr',
                    'zp': 'magzpsci',
                    'zpsys': 'zpsys',
                    }

        data = {sname: epoch_dict[zname] for sname, zname in col_map.items()}
        data['band'] = [f'ztf{val}' for val in data['band']]  # salt2 registered bandpass name

        epoch_tbl = Table(data)

        # S/N
        SN = epoch_dict['flux'] / epoch_dict['fluxerr']
        # find max S/N
        maxSN = np.max(SN)
        # find mjd of first epoch with S/N above 5 (to constrain t0)
        SNabove5 = np.where(SN>5)[0]
        mjd_SNabove5 = epoch_dict['mjd'][SNabove5[0]] if len(SNabove5)>0 else None

        # check number of detections, see is_transient()
        num_detections = np.sum(epoch_dict['isdiffpos'] == 't')

        stats = {   'maxSN': maxSN,
                    'mjd_SNabove5': mjd_SNabove5,
                    'num_detections': num_detections,
                }
        return (epoch_tbl, stats)

    def num_detections(self, epoch_dict):
        # want minimum number of positive subtractions (detections) before fitting with Salt2
        where_detected = (epoch_dict['isdiffpos'] == 't')
        return np.sum(where_detected)
