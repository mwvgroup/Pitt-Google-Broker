#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Pull files from a Storage bucket and publish to a Pub/Sub topic."""

import os

from flask import Flask, request
from google.cloud import logging

from . import bucket_to_pubsub, verify_pubsub


app = Flask(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# connect to the logger
logging_client = logging.Client()
log_name = "component-tests"  # same log for all broker instances
logger = logging_client.logger(log_name)


@app.route("/bucket_to_pubsub", methods=["POST"])
def run_bucket_to_pubsub_service():
    """Entry point for the bucket_to_pubsub service."""
    envelope = request.get_json()

    # verify the message format
    envelope_error = verify_envelope(envelope)
    if envelope_error:
        return envelope_error

    # run the service
    try:
        result = bucket_to_pubsub.run(envelope)

    except Exception as e:
        # return a server error code
        return (f"{e}", 500)

    else:
        # return success code along with the result
        return (result, 200)


@app.route("/bucket_to_pubsub", methods=["POST"])
def run_verify_pubsub_service():
    """Entry point for the verify_pubsub service."""
    envelope = request.get_json()

    # verify the message format
    envelope_error = verify_envelope(envelope)
    if envelope_error:
        return envelope_error

    # run the service
    try:
        verify_pubsub.run(envelope)

    except Exception as e:
        # return a server error code
        return (f"{e}", 500)

    else:
        # return success code
        return ("", 204)


def verify_envelope(envelope):
    """Return a 400 code if the envelope format is not as-expected."""
    envelope_error = None

    # do some checks
    if not envelope:
        msg = "no Pub/Sub message received"
        print(f"error: {msg}")
        envelope_error = (f"Bad Request: {msg}", 400)

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "invalid Pub/Sub message format"
        print(f"error: {msg}")
        envelope_error = (f"Bad Request: {msg}", 400)

    return envelope_error


if __name__ == "__main__":
    PORT = int(os.getenv("PORT")) if os.getenv("PORT") else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host="127.0.0.1", port=PORT, debug=True)
