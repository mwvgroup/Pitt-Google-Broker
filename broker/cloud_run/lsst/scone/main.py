#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Classify an alert using SCONE (Qu et al. 2021).

This code is intended to be containerized and deployed to Google Cloud Run.
Once deployed, individual alerts in the "trigger" stream will be delivered to the container as HTTP requests.
"""

import os
from pathlib import Path
import flask  # Manage the HTTP request containing the alert
import pittgoogle  # Manipulate the alert and interact with cloud resources

import google.cloud.logging
import numpy as np
import pandas as pd
import tensorflow as tf
import george
from george import kernels
from scipy.optimize import minimize
from functools import partial

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
google.cloud.logging.Client().setup_logging()

# These environment variables are defined when running the deploy.sh script.
PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# provenance variables
MODULE_NAME = "SCONE"
MODULE_VERSION = 0.1

# classifier variables
model_dir_name = ""
model_file_name = ""
MODEL_PATH = Path(__file__).resolve().parent / model_dir_name / model_file_name

# Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match setup.sh
band_to_wave = {
    "u": 3670.69,  # 2017 era, LSST-approx without atmos-trans
    "g": 4826.85,
    "r": 6223.24,
    "i": 7545.98,
    "z": 8590.90,
    "Y": 9710.28,
}

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# GCP resources used in this module
# pittgoogle will construct the full resource names from the MODULE_NAME, SURVEY, and TESTID
TOPIC = pittgoogle.Topic.from_cloud(
    MODULE_NAME, survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
TOPIC_BIGQUERY_IMPORT_SUPERNNOVA = pittgoogle.Topic.from_cloud(
    "bigquery-import-SCONE", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

TOPIC_BIGQUERY_IMPORT_CLASSIFICATIONS = pittgoogle.Topic.from_cloud(
    "bigquery-import-classifications", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Classify the alert; publish and store results.

    This module is intended to be deployed as a Cloud Run service. It will operate as an HTTP endpoint
    triggered by Pub/Sub messages. This function will be called once for every message sent to this route.
    It should accept the incoming HTTP request and return a response.

    Returns
    -------
    response : tuple(str, int)
        Tuple containing the response body (string) and HTTP status code (int). Flask will convert the
        tuple into a proper HTTP response. Note that the response is a status message for the web server
        and should not contain the classification results.
    """
    # extract the envelope from the request that triggered the endpoint
    # this contains a single Pub/Sub message with the alert to be processed
    envelope = flask.request.get_json()

    # unpack the alert. raises a `BadRequest` if the envelope does not contain a valid message
    try:
        alert = pittgoogle.Alert.from_cloud_run(envelope, "lsst")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # create heatmap and classify
    heatmap = _create_heatmap(alert)
    # scone_dict = predict(heatmap)

    # prepare data for publishing
    # classifier_summary = _classification_summary(scone_dict)
    # scone_alert = _create_outgoing_alert(alert, scone_dict)
    # scone_results = pittgoogle.Alert.from_dict(payload=scone_dict)

    # publish
    # TOPIC.publish(scone_alert, serializer="json")
    # TOPIC_BIGQUERY_IMPORT_CLASSIFICATIONS.publish(classifier_summary, serializer="json")
    # TOPIC_BIGQUERY_IMPORT_SUPERNNOVA.publish(scone_results, serializer="json")

    return "", HTTP_204


def _create_heatmap(alert: pittgoogle.Alert, fit_on_full_lc=True):
    """
    Modified function obtained from:
    https://github.com/helenqu/scone/blob/26d2094b86e554dacc98eceaa680ca4faa5a53dc/create_heatmaps/base.py#L175
    """
    # define parameters
    mjd_minmax = [-30, 150]  # value pre-defined by SCONE for CreateHeatmapsFull class instances
    milkyway_ebv = 0.0019738385

    # create heatmap using alert data
    sn_lcdata, mjd_range = _get_sn_data(alert, mjd_minmax)
    wave = [band_to_wave[elem] for elem in sn_lcdata["passband"]]
    gp = build_gp(20, sn_lcdata, wave)
    predictions, prediction_errs = _get_predictions_heatmap(gp, mjd_range, milkyway_ebv)
    heatmap = np.dstack((predictions, prediction_errs))

    return heatmap


def _get_sn_data(alert: pittgoogle.Alert, mjd_minmax) -> np.ndarray:
    """
    Modified function obtained from:
    https://github.com/helenqu/scone/blob/26d2094b86e554dacc98eceaa680ca4faa5a53dc/create_heatmaps/base.py#L353
    """
    # organize alert data for SCONE
    sn_lcdata = _format_for_classifier(alert)

    # CHECKPOINT
    # ensure photometric information is available and positive
    if len(sn_lcdata) == 0 or np.all(sn_lcdata["mjd"] < 0):
        return None

    # ensure filters in alert data are what SCONE expects
    expected_filters = list(band_to_wave.keys())
    sn_lcdata = sn_lcdata[np.isin(sn_lcdata["passband"], expected_filters)]
    if len(sn_lcdata) == 0:
        return None

    # calculate mjd range
    mjd_range = _calculate_mjd_range(sn_lcdata, mjd_minmax)
    if not mjd_range:
        return None

    # extend light curve to include very early & late epoch with zero flux.
    # Beware to pass flux_err > 0 to avoid divide-by-zero in build_gp.
    mjd_early = min(sn_lcdata["mjd"]) - 100
    mjd_late = max(sn_lcdata["mjd"]) + 100
    flux = 0.0
    flux_err = 0.1
    band = expected_filters[2]
    additional_rows = pd.DataFrame(
        {
            "object_id": [alert.objectid] * 2,
            "mjd": [mjd_early, mjd_late],
            "flux": [flux, flux],
            "flux_err": [flux_err, flux_err],
            "passband": [band, band],
        }
    )
    lcdata = pd.concat([sn_lcdata, additional_rows], ignore_index=True)

    return sn_lcdata, mjd_range


def _format_for_classifier(alert: pittgoogle.Alert) -> pd.DataFrame:
    """Create a DataFrame for input to SCONE."""
    alert_df = alert.dataframe
    scone_df = pd.DataFrame(
        data={
            # select a subset of columns and rename them for SCONE
            # get_key returns the name that the survey uses for a given field
            # for the full mapping, see alert.schema.map
            "object_id": [alert.objectid] * len(alert_df.index),
            "mjd": alert_df[alert.get_key("mjd")[1]],
            "flux": alert_df[alert.get_key("flux")[1]],
            "flux_err": alert_df[alert.get_key("flux_err")[1]],
            "passband": alert_df[alert.get_key("filter")[1]],
        },
        index=alert_df.index,
    )

    return scone_df


def build_gp(guess_length_scale, sn_data, bands):
    """This is  all  taken from Avacado -
    see https://github.com/kboone/avocado/blob/master/avocado/astronomical_object.py
    In this a 2D matern kernal is used  to  model the transient. The kernel
    width in the wavelength direction is fixed. We fit for the kernel width
    in the time direction"""

    mjdall = sn_data["mjd"]
    fluxall = sn_data["flux"]
    flux_errall = sn_data["flux_err"]

    # Want to compute the scale factor that we will use...
    signal_to_noises = np.abs(fluxall) / np.sqrt(flux_errall**2 + (0.01 * np.max(fluxall)) ** 2)
    scale = np.abs(fluxall[np.argmax(signal_to_noises)])

    kernel = (0.5 * scale) ** 2 * kernels.Matern32Kernel([guess_length_scale**2, 6000**2], ndim=2)

    gp = george.GP(kernel)
    guess_parameters = gp.get_parameter_vector()

    x_data = np.vstack([mjdall, bands]).T
    gp.compute(x_data, flux_errall)

    def neg_ln_like(p):
        gp.set_parameter_vector(p)
        return -gp.log_likelihood(fluxall)

    def grad_neg_ln_like(p):
        gp.set_parameter_vector(p)
        return -gp.grad_log_likelihood(fluxall)

    bounds = [(0, np.log(1000**2))]
    bounds = [(guess_parameters[0] - 10, guess_parameters[0] + 10)] + bounds + [(None, None)]
    # check if result with/without bounds are the same

    try:
        fit_result = minimize(
            neg_ln_like, gp.get_parameter_vector(), jac=grad_neg_ln_like, bounds=bounds
        )
        gp.set_parameter_vector(fit_result.x)
        gaussian_process = partial(gp.predict, fluxall)
    except ValueError:
        return None

    return gaussian_process


def _calculate_mjd_range(sn_data, mjd_minmax) -> list:
    """
    Modified function obtained from:
    https://github.com/helenqu/scone/blob/26d2094b86e554dacc98eceaa680ca4faa5a53dc/create_heatmaps/heatmaps_types.py#L12
    """
    mjd_min, mjd_max = mjd_minmax
    mjd_range = [np.min(sn_data["mjd"]), np.max(sn_data["mjd"])]

    return mjd_range


def _get_predictions_heatmap(gp, mjd_range, milkyway_ebv):
    """
    Modified function obtained from:
    https://github.com/helenqu/scone/blob/26d2094b86e554dacc98eceaa680ca4faa5a53dc/create_heatmaps/base.py#L406
    """
    # define expected parameters
    mjd_bins = 180
    wavelength_bins = 32

    times = np.linspace(mjd_range[0], mjd_range[1], mjd_bins)
    wavelengths = np.linspace(3000.0, 10100.0, wavelength_bins)
    ext = get_extinction(milkyway_ebv, wavelengths)
    ext = np.tile(np.expand_dims(ext, axis=1), len(times))
    time_wavelength_grid = np.transpose(
        [np.tile(times, len(wavelengths)), np.repeat(wavelengths, len(times))]
    )

    predictions, prediction_vars = gp(time_wavelength_grid, return_var=True)
    ext_corrected_predictions = np.array(predictions).reshape(32, 180) + ext
    prediction_uncertainties = np.sqrt(prediction_vars).reshape(32, 180)

    return ext_corrected_predictions, prediction_uncertainties


def get_extinction(ebv, wave):
    """
    Function obtained from:
    https://github.com/helenqu/scone/blob/26d2094b86e554dacc98eceaa680ca4faa5a53dc/create_heatmaps/helpers.py#L235
    """
    avu = 3.1 * ebv

    x = 10000.0 / wave  # inverse wavelength in microns   - creates a numpy array
    xv = 1.82
    y = x - 1.82  # another numpy array

    # Creating empty arrays in which to store the final data
    aval = []
    bval = []

    # Now need to loop through each indavidual wavlength value
    for i in range(len(x)):

        if x[i] >= 0.3 and x[i] < 1.1:  # For IR data
            a = 0.574 * pow(x[i], 1.61)
            b = -0.527 * pow(x[i], 1.61)
            aval.append(a)
            bval.append(b)

        elif x[i] >= 1.1 and x[i] < 3.3:  # For Optical/NIR data
            a = (
                1.0
                + 0.17699 * y[i]
                - 0.50447 * np.power(y[i], 2)
                - 0.02427 * np.power(y[i], 3)
                + 0.72085 * np.power(y[i], 4)
                + 0.01979 * np.power(y[i], 5)
                - 0.77530 * np.power(y[i], 6)
                + 0.32999 * np.power(y[i], 7)
            )
            b = (
                1.41338 * y[i]
                + 2.28305 * np.power(y[i], 2)
                + 1.07233 * np.power(y[i], 3)
                - 5.38434 * np.power(y[i], 4)
                - 0.62251 * np.power(y[i], 5)
                + 5.30260 * np.power(y[i], 6)
                - 2.09002 * np.power(y[i], 7)
            )
            aval.append(a)
            bval.append(b)

        elif x[i] >= 3.3 and x[i] < 8.0:  # For UV data
            if x[i] >= 5.9:
                fa = -0.04473 * np.power(x[i] - 5.9, 2) - 0.009779 * np.power(x[i] - 5.9, 3)
                fb = 0.21300 * np.power(x[i] - 5.9, 2) + 0.120700 * np.power(x[i] - 5.9, 3)
            else:
                fa = fb = 0.0

            a = 1.752 - 0.316 * x[i] - 0.104 / (np.power(x[i] - 4.67, 2) + 0.341) + fa
            b = -3.090 + 1.825 * x[i] + 1.206 / (np.power(x[i] - 4.62, 2) + 0.263) + fb

            aval.append(a)
            bval.append(b)

        elif x[i] >= 8.0 and x[i] <= 10.0:  # For Far-UV data
            a = (
                -1.073
                - 0.628 * (x[i] - 8.0)
                + 0.137 * np.power(x[i] - 8.0, 2)
                - 0.070 * np.power(x[i] - 8.0, 3)
            )
            b = (
                13.670
                + 4.257 * (x[i] - 8.0)
                - 0.420 * np.power(x[i] - 8.0, 2)
                + 0.374 * np.power(x[i] - 8.0, 3)
            )

            aval.append(a)
            bval.append(b)
        else:
            a = b = 0.0

            aval.append(a)
            bval.append(b)

    aval = np.array(aval)
    bval = np.array(bval)

    RV = 3.1
    extinct = avu * (aval + bval / RV)

    return extinct


# def run(self):
#     tf.random.set_seed(self.seed)

#     self.t_start = time.time()
#     self.trained_model = None

#     if self.external_trained_model:
#         logging.info(f"loading trained model found at {self.external_trained_model}")
#         self.trained_model = models.load_model(
#             self.external_trained_model, custom_objects={"Reshape": self.Reshape}
#         )

#     dataset, size = self._retrieve_data(self._load_dataset())
#     logging.info(f"running scone prediction on full dataset of {size} examples")
#     predict_dict, acc = self.predict(dataset)

#     return predict_dict, acc


# def _retrieve_data(self, raw_dataset):
#     dataset_size = sum([1 for _ in raw_dataset])
#     dataset = raw_dataset.map(
#         lambda x: get_images(x, self.input_shape, self.with_z), num_parallel_calls=40
#     )

#     return dataset.apply(tf.data.experimental.ignore_errors()), dataset_size


# def _load_dataset(self):
#     if type(self.heatmaps_paths) == list:
#         filenames = [
#             "{}/{}".format(heatmaps_path, f.name)
#             for heatmaps_path in self.heatmaps_paths
#             for f in os.scandir(heatmaps_path)
#             if "tfrecord" in f.name
#         ]
#     else:
#         filenames = [
#             "{}/{}".format(self.heatmaps_paths, f.name)
#             for f in os.scandir(self.heatmaps_paths)
#             if "tfrecord" in f.name
#         ]


# def get_images(raw_record, input_shape, with_z=False):
#     image_feature_description = {
#         "label": tf.io.FixedLenFeature([], tf.int64),
#         "image_raw": tf.io.FixedLenFeature([], tf.string),
#         "id": tf.io.FixedLenFeature([], tf.int64),
#     }
#     if with_z:
#         image_feature_description["z"] = tf.io.FixedLenFeature([], tf.float32)
#         image_feature_description["z_err"] = tf.io.FixedLenFeature([], tf.float32)

#     example = tf.io.parse_single_example(raw_record, image_feature_description)
#     image = tf.reshape(tf.io.decode_raw(example["image_raw"], tf.float64), input_shape)
#     image = image / tf.reduce_max(image[:, :, 0])

#     # TODO: have to subtract 1 from label to get rid of KN in early classification dataset
#     if with_z:
#         output = [
#             {"image": image, "z": example["z"], "z_err": example["z_err"]},
#             {"label": example["label"]},
#             {"id": tf.cast(example["id"], tf.int32)},
#         ]
#     else:
#         output = [
#             {"image": image},
#             {"label": example["label"]},
#             {"id": tf.cast(example["id"], tf.int32)},
#         ]
#     return output


# def predict(dataset, dataset_ids=None):

#     dataset = (
#         dataset.cache()
#     )  # otherwise the rest of the dataset operations won't return entries in the same order
#     dataset_no_ids = dataset.map(lambda image, label, *_: (image, label)).batch(self.batch_size)

#     predictions = self.trained_model.predict(dataset_no_ids, verbose=0)

#     if self.categorical:
#         predictions = np.argmax(
#             predictions, axis=1
#         )  # TODO: is this the best way to return categorical results? doesnt preserve confidence info
#     predictions = predictions.flatten()

#     true_labels = dataset.map(lambda _, label, *args: label["label"])
#     df_dict = {"pred_labels": predictions, "true_labels": list(true_labels.as_numpy_iterator())}
#     ids = dataset.map(lambda _, label, id_: id_["id"])
#     df_dict["snid"] = list(ids.as_numpy_iterator())

#     prediction_ints = np.round(predictions)
#     acc = float(
#         np.count_nonzero((prediction_ints - list(true_labels.as_numpy_iterator())) == 0)
#     ) / len(prediction_ints)

#     return df_dict, acc
