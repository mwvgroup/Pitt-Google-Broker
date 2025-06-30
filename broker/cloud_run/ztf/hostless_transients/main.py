#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module uses the "value-added" tag alert stream to identify hostless transient candidates."""

import os
from typing import Dict
from astropy.io import fits
from astropy.stats import sigma_clip
import numpy as np
import pandas as pd
from google.cloud import logging
import io
import flask
import pittgoogle

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
logging.Client().setup_logging()

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match deploy.sh

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# GCP resources used in this module
TOPIC = pittgoogle.Topic.from_cloud(
    "hostless-transients", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Produces a value-added alert stream (${survey}-hostless-transients) identifying hostless transient candidates
    Messages in this stream retain fields from the original alert-lite packet.

    This module is intended to be deployed as a Cloud Run service. It will operate as an HTTP endpoint
    triggered by Pub/Sub messages. This function will be called once for every message sent to this route.
    It should accept the incoming HTTP request and return a response.

    Returns
    -------
    response : tuple(str, int)
        Tuple containing the response body (string) and HTTP status code (int). Flask will convert the
        tuple into a proper HTTP response. Note that the response is a status message for the web server.
    """
    # extract the envelope from the request that triggered the endpoint
    # this contains a single Pub/Sub message with the alert to be processed
    envelope = flask.request.get_json()
    try:
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, schema_name="default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # define configs
    configs = {
        "sigma_clipping_kwargs": {"sigma": 3, "maxiters": 10},
        "hostless_detection_with_clipping": {
            "crop_radius": 7,
            "max_number_of_pixels_clipped": 5,
            "min_number_of_pixels_clipped": 3,
        },
    }

    if _is_candidate(alert_lite, configs):
        TOPIC.publish(
            pittgoogle.Alert.from_dict(
                {"alert": alert_lite.dict},
                attributes={**alert_lite.attributes, **{"pg_hostless_transient": "likely"}},
                schema_name="default",
            )
        )
    return "", HTTP_204


def _is_candidate(alert_lite: pittgoogle.Alert, configs: Dict) -> bool:
    # apply sigma clipping to the bytes data for each stamp
    cutouts = ["Template", "Science"]
    template_stamp, science_stamp = [alert_lite.dict.get(f"cutout{cutout}") for cutout in cutouts]
    template_stamp_clipped = sigma_clip(
        _read_stamp_data(template_stamp), **configs["sigma_clipping_kwargs"]
    )
    science_stamp_clipped = sigma_clip(
        _read_stamp_data(science_stamp), **configs["sigma_clipping_kwargs"]
    )

    return _run_hostless_detection_with_clipped_data(
        science_stamp_clipped, template_stamp_clipped, configs
    )


def _read_stamp_data(cutout):
    hdul = fits.open(io.BytesIO(cutout))

    return hdul[0].data


def _run_hostless_detection_with_clipped_data(
    science_stamp: np.ndarray, template_stamp: np.ndarray, configs: Dict
) -> bool:
    """Adapted from:
    https://github.com/COINtoolbox/extragalactic_hostless/blob/main/src/pipeline_utils.py#L271

    Detects potential hostless candidates with sigma clipped stamp images by cropping an image patch from the center of
    the image. If pixels are rejected in scientific image but not in corresponding template image, such candidates are
    flagged as potential hostless.
    """

    science_clipped = sigma_clip(science_stamp, **configs["sigma_clipping_kwargs"])
    template_clipped = sigma_clip(template_stamp, **configs["sigma_clipping_kwargs"])
    is_hostless_candidate = _check_hostless_conditions(
        science_clipped, template_clipped, configs["hostless_detection_with_clipping"]
    )

    if is_hostless_candidate:
        return is_hostless_candidate
    science_stamp = _crop_center_patch(
        science_stamp, configs["hostless_detection_with_clipping"]["crop_radius"]
    )
    template_stamp = _crop_center_patch(
        template_stamp, configs["hostless_detection_with_clipping"]["crop_radius"]
    )
    science_clipped = sigma_clip(science_stamp, **configs["sigma_clipping_kwargs"])
    template_clipped = sigma_clip(template_stamp, **configs["sigma_clipping_kwargs"])
    is_hostless_candidate = _check_hostless_conditions(
        science_clipped, template_clipped, configs["hostless_detection_with_clipping"]
    )

    return is_hostless_candidate


def _crop_center_patch(input_image: np.ndarray, patch_radius: int = 12) -> np.ndarray:
    """Adapted from:
    https://github.com/COINtoolbox/extragalactic_hostless/blob/main/src/pipeline_utils.py#L234

    Crops rectangular patch around image center with a given patch scale.
    """
    image_shape = input_image.shape[0:2]
    center_coords = [image_shape[0] / 2, image_shape[1] / 2]
    center_patch_x = int(center_coords[0] - patch_radius)
    center_patch_y = int(center_coords[1] - patch_radius)

    return input_image[
        center_patch_x : center_patch_x + patch_radius * 2,
        center_patch_y : center_patch_y + patch_radius * 2,
    ]


def _check_hostless_conditions(
    science_clipped: np.ndarray, template_clipped: np.ndarray, detection_config: Dict
) -> bool:
    """Adapted from:
    https://github.com/COINtoolbox/extragalactic_hostless/blob/main/src/pipeline_utils.py#L253
    """

    science_only_detection = (
        np.ma.count_masked(science_clipped) > detection_config["max_number_of_pixels_clipped"]
        and np.ma.count_masked(template_clipped) < detection_config["min_number_of_pixels_clipped"]
    )
    template_only_detection = (
        np.ma.count_masked(template_clipped) > detection_config["max_number_of_pixels_clipped"]
        and np.ma.count_masked(science_clipped) < detection_config["min_number_of_pixels_clipped"]
    )

    if science_only_detection or template_only_detection:
        return True

    return False
