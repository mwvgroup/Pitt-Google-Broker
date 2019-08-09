import numpy as np
from astropy.coordinates import SkyCoord
from astroquery.irsa_dust import IrsaDust

from . import xmatch as xm
from . import classify as classify


def get_value_added(alert_list, survey='ZTF'):
    """ Calculates (or looks up) all value added products for each alert in alert_list.

    Args:
        alert_list (list): list of alert dicts
        survey      (str): name of survey generating the alerts

    Returns:
        Lists of dictionaries of value added products.
    """

    # Cross Matches
    xmatch_dicts_list = xm.get_xmatches(alert_list, survey=survey) # list of dictionaries

    # Classification
    # RAPID
    light_curves, cx_data = format_for_rapid(alert_list, xmatch_dicts_list, survey=survey)
    if len(light_curves) > 0:
        class_dicts_list = classify.rapid(light_curves, cx_data, plot=False, use_redshift=True)
    else:
        print('\nThere are no alerts with enough information for classification.\n')
        class_dicts_list = []

    return xmatch_dicts_list, class_dicts_list


def format_for_rapid(alert_list, xmatch_list, survey='ZTF'):
    """ Creates a list of tuples formatted for RAPID classifier.

    Args:
        alert_list  (list): list of alert dicts
        xmatch_list (list): list of cross matched objects as given by xm.get_xmatches()
        survey       (str): name of survey generating the alerts

    Returns:
        light_curves (list): list of tuples formatted as required for input to RAPID.

        cx_data      (list): list of dicts of candidate and xmatch info as needed for
                             upload to BigQuery classification table.

    """
    # throw an error if received non-ZTF data
    assert (survey=='ZTF'), "\nvalue_added.format_for_rapid() requires survey=='ZTF'"

    light_curves = []
    cx_dicts = {} # collect candidate and xmatch data to merge with RAPID results
    oid_map = map_objectId_list(xmatch_list) # maps objectId's to list positions

    for alert in alert_list:
        oid = alert['objectId']
        cid = alert['candidate']['candid']
        cand_mjd = jd_to_mjd(alert['candidate']['jd'])
        ra = alert['candidate']['ra']
        dec = alert['candidate']['dec']

        # Observation epoch data
        fid_dict = {1:'g', 2:'r', 3:'i'}
        mjd, flux, fluxerr, passband, photflag = ([] for i in range(5))

        for epoch in alert['prv_candidates'] + [alert['candidate']]:
            try:
                assert epoch['magpsf'] is not None # magpsf is null for nondetections
                # test this. try setting magnitude to epoch['diffmaglim'] instead of skipping.
            except:
                pass

            else:
                mjd.append(jd_to_mjd(epoch['jd']))
                f, ferr = mag_to_flux(epoch['magpsf'],epoch['magzpsci'],epoch['sigmapsf'])
                flux.append(f)
                fluxerr.append(ferr)
                passband.append(fid_dict[epoch['fid']])
                photflag.append(4096)  # fix this, determines trigger time
                                    # (1st mjd where this == 6144)
        # Set trigger date. fix this.
        photflag[np.where(flux==np.max(flux))[0][0]] = 6144

        # skip classification if don't have g passband
        if 'g' not in passband: continue

        # MW dust extinction
        # fix this. ZTF docs say ra, dec are in J2000 [deg]
        coo = SkyCoord(ra, dec, frame='icrs', unit='deg')
        dust = IrsaDust.get_query_table(coo, section='ebv')
        mwebv = dust['ext SandF mean'][0]

        # classify for each xmatch host galaxy
        xm_indicies = oid_map[oid]
        for xm in xm_indicies:
            xmatch = xmatch_list[xm]
            xobjId = xmatch['xobjId']
            xcatalog = xmatch['xcatalog']

            # skip classification if xobject is not a galaxy
            if xmatch['sgscore'] < 0.75: continue
            # skip classification if xobject redshift == -1
            redshift = xmatch['redshift']
            if redshift < 0: continue

            # get unique alert-hostgal id
            # this ID is currently *only* used for RAPID *input*, it can be anything
            cxid = alert_xobj_id([oid, cid, cand_mjd, xcatalog, xobjId ])

            # Collect all the info
            light_curves.append((np.asarray(mjd), np.asarray(flux), np.asarray(fluxerr), \
                                np.asarray(passband), np.asarray(photflag), \
                                ra, dec, cxid, redshift, mwebv))

            cx_dicts[cxid] = {   'objectId': oid,
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

    if type(data) == list:
        assert len(data)==5, 'alert_xobj_id() received invalid data list.'
        data = [ str(d) for d in data ] # convert to strings
        return '-'.join(data)

    elif type(data) == str:
        return data.split('-')

    else:
        assert False, 'alert_xobj_id() received invalid data type.'
    return None


def map_objectId_list(dict_list):
    """ Creates a mapping between list indicies and objectId's.

    Args:
        dict_list: list of dictionaries. Each dict must include key 'objectId'

    Returns:
        dictionary with key = objectId, value = list of dict_list indicies matching objectId
    """

    d = {}
    for idx, dict in enumerate(dict_list):
        oid = dict['objectId']
        try:
            indicies = d[oid] + [idx]
        except KeyError:
            indicies = [idx]
        d[oid] = indicies

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
    return jd - 2400000.5
