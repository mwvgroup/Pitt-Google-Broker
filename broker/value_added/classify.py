from astrorapid.classify import Classify


def rapid(light_curves, cx_data, plot=False, plotdir='./broker/value_added/plots', use_redshift=True):
    """ Classifies alerts using RAPID (aka astrorapid).

    Args:
        light_curves  (list of tuples): light_curve_info for multiple objects,
                                        where light_curve_info =
                                        (mjd, flux, fluxerr, passband,
                                        photflag, ra, dec, objid, redshift, mwebv)

        cx_data        (list of dicts): candidate and xmatch info as needed for
                                        BigQuery classification table.
        Note:
            A given index must identify the same unique object + host galaxy combination
            in both the light_curves and cx_data lists.
            Use the function value_added.format_for_rapid() to get both lists.

    Returns:
        List of dictionaries formatted for upload to BigQuery classification table.
    """

    classification = Classify(known_redshift=use_redshift)
    predictions = classification.get_predictions(light_curves, return_predictions_at_obstime=True)

    if plot:
        # Plot classifications vs time
        classification.plot_light_curves_and_classifications(figdir=plotdir)
        # classification.plot_classification_animation(figdir=plotdir)
        print('\nRAPID classification plot(s) saved to {}'.format(plotdir))
        print("Pass arg 'plotdir' to change this location.")

    class_dicts_list = format_rapid_for_BQ(cx_data, predictions)

    return class_dicts_list


def format_rapid_for_BQ(cx_data, predictions):
    """ Combines RAPID output with candidate and xmatch data and formats for upload to BigQuery.

    Args:
        cx_data        (list of dicts): candidate and xmatch info as needed for
                                        BigQuery classification table.

        predictions            (tuple): as returned by rapid function get_predictions()

    Returns:
        cx_data with candidate epoch classification info added to each dictionary.
    """

    classes_list, times_list = predictions # lists of arrays

    # Check that all light curves were classified
    err_msg = "Number of predictions from RAPID != Number of input light curves. \
                \nCannot match predictions to candid's."
    assert len(classes_list) == len(cx_data), err_msg

    # Merge predicitions with alert and hostgal info
    class_dicts_list = []
    for lc_preds, lc_times, cx_dict in zip(classes_list, times_list, cx_data):
        # Get the predictions for the current alert candidate only
        cand_preds = lc_preds[-1] # check this.
        # I tried to match the candidate mjd (see below), but the output times are
        # not exactly the same as the input times.
        class_keys = ['prob_class{}'.format(i) for i in range(len(cand_preds))] # fix this.
        preds_dict = dict(zip(class_keys, cand_preds.tolist()))
        # # find position of cand_mjd in lc_times array
        # cand_mjd = cx_dict.pop('cand_mjd') # this is not sent to BQ
        # cand_idx = lc_times == cand_mjd # array of bools
        # # get the class predictions for the alert candidate, ensure exactly 1 match
        # cand_preds = lc_preds[cand_idx] # array of classification arrays
        # if len(cand_preds) == 1:
        #     cand_preds = cand_preds[0] # array of class predictions for candidate epoch
        #     class_keys = [str(i) for i in range(len(cand_preds))]
        #     preds_dict = dict(zip(class_keys, cand_preds.tolist()))
        # else:
        #     print(cx_dict)
        #     print(cand_mjd, lc_times)
        #     err_msg = "Found {} RAPID classification predictions at \
        #                 observation time = candidate mjd. \
        #                 \n(Exactly 1 match is required.)".format(len(cand_preds))
        #     assert False, err_msg

        class_dicts_list.append({**cx_dict, **preds_dict})

    return class_dicts_list
