#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Classify alerts using AutoTune (Parlange et al. 2026)."""

import os
import io
import numpy as np
import flask
import pittgoogle
import timm
import torch
from astropy.io import fits
from google.cloud import logging
from safetensors.torch import load_file
from torchvision import transforms
from huggingface_hub import hf_hub_download
from pathlib import Path

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
logging.Client().setup_logging()

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# ---Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match deploy.sh

# ---Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# ---GCP resources used in this module
TOPIC = pittgoogle.Topic.from_cloud("autotune", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run() -> tuple[str, int]:
    """Classify alert with AutoTune; publish and store results.

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
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, "default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    cutouts = _get_cutouts(alert_lite.dict)
    autotune_dict = _classify(cutouts)

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {"alert_lite": alert_lite.dict["alert_lite"], "autotune": autotune_dict},
            attributes={
                **alert_lite.attributes,
                "pg_autotune_class": autotune_dict["predicted_class"],
            },
            schema_name="default",
        )
    )

    return "", HTTP_204


def _classify(cutouts: np.ndarray) -> dict:

    # load model
    model_path = hf_hub_download(
        repo_id="parlange/autotune-models",
        filename="autotune_btsbot_optuna_asha/model.safetensors",
    )
    state_dict = load_file(model_path)
    model = timm.create_model("deit3_base_patch16_224", pretrained=False, num_classes=2)
    model.load_state_dict(state_dict, strict=False)
    model.eval()

    # inference
    transform = transforms.Compose(
        [
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    # classify
    input_tensor = transform(cutouts).unsqueeze(0)
    with torch.no_grad():
        output = model(input_tensor)
        prediction = torch.softmax(output, dim=1)

    autotune_dict = {
        "prob_class0": prediction[0, 0].item(),
        "prob_class1": prediction[0, 1].item(),
        "predicted_class": np.argmax(prediction).item(),
    }

    return autotune_dict


def _get_cutouts(alert_lite_dict: pittgoogle.Alert) -> np.ndarray:
    """Extract cutouts from the alert dictionary and return a numpy array."""
    cutout_labels = ["Science", "Template", "Difference"]
    cutouts = []

    for label in cutout_labels:
        key = f"cutout{label}"
        cutout_bytes = alert_lite_dict[key]
        cutout = _decode_cutout(cutout_bytes)
        cutouts.append(cutout)

    image = np.stack(cutouts, axis=-1)

    return image


def _decode_cutout(cutout_bytes):
    """Decode the FITS data from a byte string and return a numpy array."""
    with fits.open(io.BytesIO(cutout_bytes)) as hdul:
        return hdul[0].data
