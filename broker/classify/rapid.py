import pandas as pd
import numpy as np
from broker.ztf_archive import _parse_data as psd
from astrorapid.classify import Classify
from sklearn.externals import joblib

from astropy.coordinates import SkyCoord
from astroquery.irsa_dust import IrsaDust

# fs SETUP
# had to manually update the following:
# pip install wrapt --upgrade --ignore-installed
# pip install setuptools --upgrade
# pip install protobuf --upgrade
# then the following succeeded:
# pip install astrorapid

# fe SETUP

def classify(light_curves, plot=True, use_redshift=True):
    """ Classifies alerts using RAPID (aka astrorapid).

    Args:
        light_curves (list of tuples): light_curve_info for multiple objects,
            where light_curve_info = (mjd, flux, fluxerr, passband, zeropoint, \
                                        photflag, ra, dec, objid, redshift, mwebv)

    Returns:
        List of tuples where each tuple contains predicted probabilities
        of each class for a single object.
    """

    classification = Classify(known_redshift=use_redshift)
    predictions = classification.get_predictions(light_curves)
    # print(predictions)

    if plot:
        # Plot classifications vs time
        figdir='./tests/rapid/classifications'
        classification.plot_light_curves_and_classifications(figdir=figdir)
        # classification.plot_classification_animation(figdir=figdir)

    return predictions


def format_alert_data(alert):
    """ Takes a dict of observation data and returns a tuple formatted for RAPID classifier.

    Args:
        alert (dict):   Needs the following key:value pairs
                        'objectId'  : (int) unique for each object
                        'ra'        : (float) right ascension
                        'dec'       : (float) declination
                        'hostgal'   : (dict) ??? (used to calculate redshift)
                        'Obs'       : (list of dicts) one entry per epoch.
                                        Each dict needs the following key:value pairs
                                        'mjd'       : () modified julian date
                                        'flux'      : (float)
                                        'fluxerr'   : (float)
                                        'passband'  : (str)
                                        'photflag'  : ()

    Returns:
        Tuple of light curve data, Formatted as required for input to RAPID classifier.
    """

    # Redshift
    redshift = calc_redshift(alert['hostgal']) # fix this

    # MW dust extinction
    # fix this. ZTF docs say ra, dec are in J2000 [deg]
    coo = SkyCoord(alert['ra'], alert['dec'], frame='icrs', unit='deg')
    dust = IrsaDust.get_query_table(coo, section='ebv')
    mwebv = dust['ext SandF mean'][0]

    # collect data from each epoch
    mjd, flux, fluxerr, passband, zeropoint, photflag = ([] for i in range(6))
    for c, cdat in enumerate(alert['Obs']):
        mjd.append(cdat['mjd'])
        flux.append(cdat['flux'])
        fluxerr.append(cdat['fluxerr'])
        passband.append(cdat['passband'])
        photflag.append(cdat['photflag'])

    # fix this. set trigger date
    photflag[np.where(flux==np.max(flux))[0][0]] = 6144

    light_curve_info = (np.asarray(mjd), np.asarray(flux), np.asarray(fluxerr), \
                        np.asarray(passband), np.asarray(photflag), \
                        alert['ra'], alert['dec'], alert['objectId'], redshift, mwebv)
    return light_curve_info


def collect_ZTF_alerts(max_alerts=10):
    """ Iterates through previously downloaded ZTF alerts and returns
        list of light curve data for classification.

    Args:
        max_alerts (int):   Max number of alerts to collect. (Default: 10)
                            Set to negative number for all alerts.

    Returns:
        light_curves (list of tuples): Formatted as required for input to RAPID classifier.

    """

    light_curves = [] # collect alert data for ar.Classify
    for a, alert in enumerate(psd.iter_alerts()):
        cand = alert['candidate']

        # Collecting alert data for format_alert_data()
        dict = {'objectId'  : alert['objectId'],
                'ra'        : cand['ra'],
                'dec'       : cand['dec'],
                }

        # Host Galaxy: get list of possible host galaxies, used to calculate redshift
        hostgal_lst = []
        zcols_pre = ['sgscore', 'sgmag', 'srmag', 'simag', 'szmag']
        for s in [1,2,3]:
            zcols = [ c + str(s) for c in zcols_pre ]
            if cand[zcols[0]] < 0.75: # fix this threshold value
                continue # if it's not a galaxy, move to the next source
            else:
                hostgal_lst.append({zcols_pre[1][1:]: cand[zcols[1]],
                                    zcols_pre[2][1:]: cand[zcols[2]],
                                    zcols_pre[3][1:]: cand[zcols[3]],
                                    zcols_pre[4][1:]: cand[zcols[4]],
                                    }) # fix this, may need to convert magnitudes
                break
        try:
            len(hostgal_lst) > 0
        except:
            continue # fix this.. what to do when no known host gal

        # Observation epoch data
        fid_dict = {1:'g', 2:'r', 3:'i'}
        dict['Obs'] = []
        passbands = [] # keep track of these for later data cuts
        for c, cdat in enumerate([cand] + alert['prv_candidates']):
            try:
                assert cdat['magpsf'] is not None # magpsf is null for nondetections
                # test this. try setting the magnitude to cdat['diffmaglim'] instead of skipping.
            except:
                # print('Object {}, epoch {} has a nondetection.'.format(dict['objectId'], c))
                pass
            else:
                flux, fluxerr = mag_to_flux(cdat['magpsf'], cdat['magzpsci'], cdat['sigmapsf'])
                obs = { 'mjd'       : jd_to_mjd(cdat['jd']),
                        'flux'      : flux,
                        'fluxerr'   : fluxerr,
                        'passband'  : fid_dict[cdat['fid']], # fix this, no entry for z band
                        'photflag'  : 0 # fix this, determines trigger time (1st mjd where this == 6144)
                }

                dict['Obs'].append(obs)
                passbands.append(obs['passband'])

        # Cut alerts without enough info to classify
        if len(dict['Obs']) < 2: # check this... can set to 1?
            continue
        if 'g' not in passbands:
            continue

        # Format data for RAPID classifier
        # classify for each possible host galaxy
        objectId = dict['objectId']
        for i, hg in enumerate(hostgal_lst):
            dict['hostgal'] = hg
            if i>0:
                dict['objectId'] = objectId+'_hostgal'+str(i+1)
                # count_multiple_hostgals = count_multiple_hostgals+1
            light_curves.append(format_alert_data(dict))


        if ((a+1) >= max_alerts) & (a !< 0):
            break

    return light_curves


def calc_redshift(mag_dict):
    """ Calculates redshift using a single pre-trained random forest model from Rongpu.
        THIS MODEL WAS TRAINED ON DECaLS DATA AND IS NOT A GOOD PREDICTOR FOR Pan-STARRS DATA!

        Args:
            mag_dict  (dict):

        Returns:
            redshift of galaxy associated with mag_dict.
    """

    # Load single pre-trained tree
    regrf = joblib.load('./regrf_20181008_0.pkl')

    gmag = mag_dict['gmag']
    rmag = mag_dict['rmag']
    zmag = mag_dict['imag']
    w1mag = mag_dict['zmag']
    w2mag = 0.

    radius, q, p = (0 for i in range(3))

    data1 = np.column_stack((gmag-rmag, rmag-zmag, zmag-w1mag, w1mag-w2mag, rmag, radius, q, p))
    z_phot = regrf.predict(data1)

    return z_phot[0]


def mag_to_flux(mag, zeropoint, magerr):
    """ Converts an AB magnitude and its error to fluxes.
    """
    flux = 10**( (zeropoint - mag)/ 2.5 )
    fluxerr = flux* magerr* np.log(10/2.5)
    return flux, fluxerr


def jd_to_mjd(jd):
    """ Converts Julian Date to modified Julian Date.
    """
    return jd - 2400000.5
