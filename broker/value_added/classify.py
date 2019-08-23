#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

""" The ``classify`` module predicts the object type/classification and
    returns the results formatted for upload to BigQuery.

    Currently using the RAPID (astrorapid) classifier.

    Helpful links:
      https://astrorapid.readthedocs.io
"""

from astrorapid.classify import Classify


def rapid(light_curves, cx_dicts, plotdir=None):
    """ Classifies alerts using RAPID (aka astrorapid).

    Args:
        light_curves (list): [light_curve_info formatted for input to RAPID.]
                             where
                             light_curve_info = (mjd, flux, fluxerr, passband,
                                                 photflag, ra, dec,
                                                 objid, redshift, mwebv)

        cx_dicts     (dict): { alert_xobj_id (str):
                             { <column name (str)>: <value (str or float)> } }
                             Values are dicts of candidate and xmatch info
                             as needed for upload to BQ classification table.
        Note:
            A given index must identify the same unique object + host galaxy
            combination in both the light_curves and cx_dicts lists.
            Use the function value_added.format_for_rapid() to get both lists.

        plotdir                  (str): Directory for classification plots.
                                        Pass None to skip plotting.

    Returns:
        Dictionaries of classification results, formatted for BigQuery.
        One dictionary per element in light_curves.
        This is cx_dicts with classification info added.
        [ {<column name (str)>: <value (str or float)>} ]

    """
    # If there is nothing to classify, return an empty list
    if len(light_curves) == 0:
        _warn('\nThere are no alerts with enough information for classification.\n')
        return []

    classification = Classify(known_redshift=True)
    predictions = classification.get_predictions(light_curves,
                        return_predictions_at_obstime=True, return_objids=True)
                  # = classes_list, times_list, objids_list
                  # lists of arrays, one array per classified object

    if plotdir is not None:
        # Plot classifications vs time
        classification.plot_light_curves_and_classifications(figdir=plotdir)
        # classification.plot_classification_animation(figdir=plotdir)

    classification_dicts = format_rapid_for_BQ(cx_dicts, predictions)

    return classification_dicts


def format_rapid_for_BQ(cx_dicts, predictions):
    """ Combines RAPID output with candidate and xmatch data and formats
        for upload to BigQuery.

    Args:
        cx_dicts (dict of dicts): candidate and xmatch info as needed for
                                  BigQuery classification table.
                                  Keys are lightcurve IDs (cxid, as given
                                  by value_added.alert_xobj_id()).

        predictions      (tuple): as returned by astrorapid's get_predictions()

    Returns:
        cx_dicts with candidate epoch classification info added to each dict.
    """

    # Merge predicitions with alert and hostgal info
    classification_dicts = []
    for lc_preds, lc_times, cxid in zip(*predictions):
        # Get the predictions for the current alert candidate only.
        # I tried to match the candidate mjd input with a rapid output,
        # but the output times are not exactly the same as the input times.
        # This should be the last prediction, but check this.
        cand_preds = lc_preds[-1]
        class_colnames = [f'prob_class{i}' for i in range(len(cand_preds))]
        preds_dict = dict(zip(class_colnames, cand_preds.tolist()))

        # Add predictions to cx_dicts
        classification_dicts.append({**cx_dicts[cxid], **preds_dict})

    return classification_dicts
