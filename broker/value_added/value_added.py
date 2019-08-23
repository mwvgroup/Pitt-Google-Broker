#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

""" This is the main module controlling the calculation, lookup, and return
    of all value added products (e.g. cross matches and classifications).

    Usage Example:

        ```python
        # get alerts
        from broker.ztf_archive import _parse_data as psd
        num_alerts = 15
        alert_list = next(psd.iter_alerts(num_alerts=num_alerts))

        # get value added products
        from broker.value_added import value_added as va
        kwargs = {'survey':'ZTF', 'rapid_plotdir':'./broker/value_added/plots'}
        xmatches, classifications = va.get_value_added(alert_list, **kwargs)
        ```
"""

from warnings import warn as _warn

import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
from astroquery.irsa_dust import IrsaDust

from . import xmatch as xm
from . import classify as classify


def get_value_added(alert_list, survey='ZTF', rapid_plotdir=None):
    """ Compiles all value added products for each alert in alert_list.

    Args:
        alert_list   (list): list of alert dicts

        survey        (str): name of survey generating the alerts

        rapid_plotdir (str): directory for RAPID classification plots.
                             Pass None to skip plotting.

    Returns:
        Lists of dictionaries of value added products, formatted for
        upload to BigQuery. One dictionary per unique alert-xmatch pair.

        xmatch_dicts [ {<column name (str)>: <value (str or float)>} ]

        classification_dicts [ {<column name (str)>: <value (str or float)>} ]

    """

    ### Cross Matches
    xmatch_dicts = xm.get_xmatches(alert_list, survey=survey)  # list of dicts
    ###

    ### Classification
    # RAPID
    light_curves, cx_dicts = format_for_rapid(alert_list, xmatch_dicts,
                                              survey=survey)
    classification_dicts = classify.rapid(light_curves, cx_dicts,
                                          plotdir=rapid_plotdir)
                                          # list of dicts
    ###

    return xmatch_dicts, classification_dicts


def format_for_rapid(alert_list, xmatch_list, survey='ZTF'):
    """ Creates a list of tuples formatted for RAPID classifier.

    Args:
        alert_list  (list): alert dicts
        xmatch_list (list): cross matched objects as given by xm.get_xmatches()
        survey       (str): name of survey generating the alerts

    Returns:
        light_curves (list): [(light curve info formatted for input to RAPID.)]

        cx_dicts     (dict): { alert_xobj_id (str):
                               {<column name (str)>: <value (str or float)> }}
                             Values are dicts of candidate and xmatch info
                             as needed for upload to BQ classification table.
                             Classification info should be added using the
                             ``classify`` module.

    """
    # throw an error if received non-ZTF data
    if survey != 'ZTF':
        raise ValueError("value_added.format_for_rapid() requires survey=='ZTF'")

    # map objectId's to xmatch list positions
    oid_map = map_objectId_list(xmatch_list)

    # Gather info for each candidate + xmatch object
    light_curves = []  # for RAPID input
    cx_dicts = dict()  # collect candidate & xmatch data to merge with RAPID results
    for alert in alert_list:
        lc, cxd = format_for_rapid_proc_alert(alert, xmatch_list, oid_map)
        light_curves.extend(lc)
        cx_dicts.update(cxd)

    return light_curves, cx_dicts


def format_for_rapid_proc_alert(alert, xmatch_list, oid_map):
    """
    Args:
        alert  (dict): single alert dictionary

        xmatch_list (list): cross matched objects as given by xm.get_xmatches()

        oid_map     (dict): mapping of oid's to position(s) in xmatch_list
                            e.g. oid_map = map_objectId_list(xmatch_list)

    Returns:
        light_curves (list): [(light curve info formatted for input to RAPID.)]

        cx_dicts     (dict): { alert_xobj_id (str):
                               {<column name (str)>: <value (str or float)>}}
                             Values are dicts of candidate and xmatch info
                             as needed for upload to BQ classification table.

    """

    # Collect data from observation epochs
    epochs = alert['prv_candidates'] + [alert['candidate']]
    epoch_data = format_for_rapid_proc_epochs(epochs)

    # Skip classification if don't have g passband
    if 'g' not in epoch_data['passband']:
        return [], dict()
    # if 'r' not in passband: continue # this hasn't been a problem yet
    # Need to find alert with no r band and see if it gets classified.
    # If not, color is important and we can replace this with:
    # if len(passband.unique()) < 2: continue

    # MW dust extinction
    # fix this. ZTF docs say ra, dec are in J2000 [deg]
    coo = SkyCoord(ra, dec, frame='icrs', unit='deg')
    dust = IrsaDust.get_query_table(coo, section='ebv')
    mwebv = dust['ext SandF mean'][0]

    # Create objects for each candidate-host galaxy pair
    light_curves, cx_dicts = format_for_rapid_proc_xmatches(alert, xmatch_list,
                                   oid_map[alert['objectId']],
                                   epoch_data, mwebv)

    return light_curves, cx_dicts


def format_for_rapid_proc_epochs(epochs):
    """ Collects data from each observation epoch of a single alert.

    Args:
        epochs (list[dict]): one dict per observation epoch

    Returns:
        epoch_dict (dict): keys: 'mjd','flux','fluxerr','passband','photflag'
                           values: Lists of light curve data with one element
                                   per epoch.
    """

    # prepare empty lists to zip epoch data
    mjd, flux, fluxerr, passband, photflag = ([] for i in range(5))
    # passband mapping
    fid_dict = {1:'g', 2:'r', 3:'i'}
    # set and track epochs with missing zeropoints
    zp_fallback, zp_in_keys = 26.0, [0 for i in range(len(epochs))]

    for epoch in epochs:
        # skip nondetections.
        if epoch['magpsf'] is None: continue
        # fix this. try setting magnitude to epoch['diffmaglim']

        # check zeropoint (early schema(s) did not contain this)
        if 'magzpsci' not in epoch.keys():  # fix this. do something better.
            _warn('Epoch does not have zeropoint data. '
                  'Setting to {}'.format(zp_fallback))
            zp_in_keys[n] = 1
            epoch['magzpsci'] = zp_fallback

        # Gather epoch data
        mjd.append(jd_to_mjd(epoch['jd']))
        f, ferr = mag_to_flux(epoch['magpsf'], epoch['magzpsci'],
                              epoch['sigmapsf'])
        flux.append(f)
        fluxerr.append(ferr)
        passband.append(fid_dict[epoch['fid']])
        photflag.append(4096)  # fix this, determines trigger time
                               # (1st mjd where this == 6144)

    # check zeropoint consistency
    # either 0 or all epochs (with detections) should be missing zeropoints
    if sum(zp_in_keys) not in [0, len(mjd)]:
        raise ValueError((f'Inconsistent zeropoint values in alert {oid}. '
                           'Cannot continue with classification.'))

    # Set trigger date. fix this.
    photflag[np.equals(flux == np.max(flux))] = 6144

    epoch_dict = { 'mjd': np.asarray(mjd),
                   'flux': np.asarray(flux),
                   'fluxerr': np.asarray(fluxerr),
                   'passband': np.asarray(passband),
                   'photflag': np.asarray(photflag)
                 }

    return epoch_dict


def format_for_rapid_proc_xmatches(alert, xmatch_list, xm_indices, epoch_data, mwebv):
    """
    Args:
        alert       (dict): single alert dictionary

        xmatch_list (list): cross matched objects as given by xm.get_xmatches()

        xm_indices  (list): indices of xmatch_list corresponding to alert objectId

        epoch_data  (dict): light curve data, as returned by
                            format_for_rapid_proc_epochs()

        mwebv      (float): Milky Way dust extinction

    Returns:
        light_curves (list): [(light curve info formatted for input to RAPID.)]

        cx_dicts     (dict): { alert_xobj_id (str):
                               { <column name (str)>: <value (str or float)> } }
                             Values are dicts of candidate and xmatch info
                             as needed for upload to BQ classification table.

    """

    # Unpack some alert data
    oid = alert['objectId']
    cid = alert['candidate']['candid']
    cand_mjd = jd_to_mjd(alert['candidate']['jd'])

    # create a new object for each candidate-host galaxy pair
    light_curves = []  # for RAPID input
    cx_dicts = dict()  # collect candidate+xmatch data to merge with RAPID results
    for i in xm_indices:
        xmatch = xmatch_list[i]
        xobjId = xmatch['xobjId']
        xcatalog = xmatch['xcatalog']
        redshift = xmatch['redshift']

        # skip classification if we don't have redshift info
        if redshift < 0: continue

        # get unique candidate-xmatch id to match RAPID input and output
        cxid = alert_xobj_id([oid, cid, cand_mjd, xcatalog, xobjId ])

        # Collect all the info
        light_curves.append((epoch_data['mjd'],
                             epoch_data['flux'],
                             epoch_data['fluxerr'],
                             epoch_data['passband'],
                             epoch_data['photflag'],
                             alert['candidate']['ra'],
                             alert['candidate']['dec'],
                             cxid,
                             redshift,
                             mwebv
                             ))

        cx_dicts[cxid] = {  'objectId': oid,
                            'candid': cid,
                            'xobjId': xobjId,
                            'xcatalog': xcatalog,
                            'redshift': redshift,
                            'cand_mjd': cand_mjd
                         }

    return light_curves, cx_dicts


def alert_xobj_id(data):
    """ Does encoding and decoding of an ID unique to each
        alert + cross matched object.

        Used as objid input to RAPID.

    Args:
        data:   (list)  [objectId, alertId, cand_mjd, xcatalog, xobjectId]
                        as strings or compatible type.
                        Returns the combined alert_xobj_id

                (str)   alert_xobj_id
                        Returns list of strings of parsed Id's
                        [objectId, alertId, cand_mjd, xcatalog, xobjectId]

    Returns:
        If data is a list of strings, returns the combined alert_xobj_id.
        If data is a string, returns list of strings of parsed Id's
    """

    if isinstance(data, list):
        # soft check that the input is as expected. fix this.
        if len(data)!=5:
            raise ValueError('alert_xobj_id() received invalid data list.')

        return '-'.join([ str(d) for d in data ])

    elif isinstance(data, str):
        return data.split('-')

    else:
        raise ValueError('alert_xobj_id() received invalid data type.')


def map_objectId_list(dict_list):
    """ Creates a mapping between list indices and objectId's.

    Args:
        dict_list (list of dicts): Each dict must include key 'objectId'

    Returns:
        { <objectID (str)>: <corresponding indices in dict_list (list[int])> }
    """

    out_dict = dict()
    for idx, d in enumerate(dict_list):
        obj_id = d['objectId']
        out_dict[obj_id] = [*out_dict.get(obj_id, []), idx]

    return d


def mag_to_flux(mag, zeropoint, magerr):
    """ Converts an AB magnitude and its error to fluxes.
    """
    flux = 10**( (zeropoint - mag)/ 2.5 )
    fluxerr = flux* magerr* np.log(10/2.5)
    return flux, fluxerr


def jd_to_mjd(jd):
    """ Converts Julian Date to modified Julian Date.
    """
    return Time(jd, format='jd').mjd
