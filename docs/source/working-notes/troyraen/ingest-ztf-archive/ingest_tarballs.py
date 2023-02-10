#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import logging
import re
import subprocess
import tempfile
import fastavro as fa
import tarfile
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from google.cloud import storage, bigquery
from google.cloud.exceptions import PreconditionFailed, NotFound
import pandas as pd
from pathlib import Path
from datetime import datetime
from urllib.request import urlretrieve
import os

from broker_utils.types import AlertFilename
import schemas


PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

LOGSDIR = FDONE = Path(__file__).parent / "logs"
LOGSDIR.mkdir(exist_ok=True)
FDONE = LOGSDIR / "done.csv"
FERR = LOGSDIR / "error.csv"
FSUB = LOGSDIR / "submitted-to-bigquery.csv"
ALERTSDIR = Path(__file__).parent / "alerts"
ALERTSDIR.mkdir(exist_ok=True)
ZTFURL = "https://ztf.uw.edu/alerts/public"

handler = logging.FileHandler(LOGSDIR / "ingest_tarballs.log")
handler.setLevel(logging.INFO)
handler.setFormatter(
    logging.Formatter(
        "[%(levelname)s] %(name)s: %(asctime)s [%(processName)s:%(threadName)s] %(message)s"
    )
)
logger = logging.getLogger()
logger.addHandler(handler)

BQ_CLIENT = bigquery.Client()
DATASET = f"{SURVEY}_alerts"
_BUCKET = f"{PROJECT_ID}-{SURVEY}-alert_avros"
if TESTID != "False":
    DATASET = f"{DATASET}_{TESTID}"
    _BUCKET = f"{_BUCKET}-{TESTID}"


def BUCKET():
    """Create new client, connect to bucket, and return it."""
    return storage.Client().get_bucket(f"{_BUCKET}")


def AVROGLOB(tarname) -> str:
    """Return glob string for .avro files with fixed schemas (relative to ALERTSDIR)."""
    tname = tarname.replace(".tar.gz", "")
    # this only matches files with fixed schemas not the original alerts extracted from the tarball
    return f"{tname}/*.{tname}.avro"


def REPORT(kind, msg):
    """Write the message to file."""
    fout = {"done": FDONE, "error": FERR, "submitted": FSUB}
    with open(fout[kind], "a") as f:
        f.write(f"{msg}\n")


class SchemaParsingError(Exception):
    """Error parsing or guessing properties of an alert schema."""

    pass


def run():
    """Ingest all tarballs from ZTF's alert archive."""
    tardf = fetch_tarball_names()
    with Pool(5) as pool:
        pool.map(ingest_one_tarball, tardf["Name"].values)


def ingest_one_tarball(tarname, nthreads=12):
    """Ingest one tarball from ZTF archive to Cloud Storage bucket and BigQuery table."""
    logging.info(f"Starting tarball {tarname}")
    apaths = download_tarball(tarname)
    # try:
    #     falert = apaths[0]
    # except IndexError:
    #     return
    falert = apaths[0]
    dalert = falert.parent

    with open(falert, "rb") as fin:
        version = guess_schema_version(fin.read())
    logging.info(f"Alert version = {version}")

    touch_schema(version, falert)
    schema = schemas.loadavsc(version=version, nocutouts=False)

    table = f"{PROJECT_ID}.{DATASET}.alerts_v{version.replace('.', '_')}"
    touch_table(table, falert, schemas.loadavsc(version, nocutouts=True), version)

    logging.info("Fixing alerts on disk")
    with ThreadPool(nthreads) as pool:
        pool.map(fix_alert_on_disk, [[f, schema, version] for f in apaths])

    bucket = BUCKET()
    success = load_alerts_to_bucket(bucket, tarname)
    if success:
        load_alerts_to_table(table, tarname, bucket)

    try:
        dalert.rmdir()
    except OSError:  # directory is not empty
        REPORT("error", f"{dalert.name},rm_dir")

    logging.info(f"Done with {tarname}")


def fix_alert_on_disk(args):
    """Load one alert, fix the schema, and write it to disk."""
    falert, schema, version = args
    alert_dict = open_alert(falert, version)
    if alert_dict is None:
        return

    filename = AlertFilename(
        {
            "objectId": alert_dict["objectId"],
            "sourceId": alert_dict["candid"],
            "topic": falert.parent.name,
            "format": "avro",
        }
    ).name
    fout = falert.parent / filename

    # fix the schema, write a new file, then delete the original alert from disk since we're done with it
    with open(fout, "wb") as f:
        fa.writer(f, schema, [alert_dict])
    falert.unlink()


def load_alerts_to_bucket(bucket, tarname):
    """Upload alerts to bucket. This is much simpler to batch and parallelize using `gsutil` command-line tool."""
    logging.info(f"Loading alerts to bucket. {tarname}")

    # gsutil:
    # -m flag runs uploads in parallel
    # macs must use multi-threading not multi-processing, specified with -o flag
    # might as well just use multi-threading to match the ThreadPool invocation of fix_alert_on_disk
    pathglob = f"{ALERTSDIR}/{AVROGLOB(tarname)}"
    cmd = ["gsutil", "-m", "-o GSUtil:parallel_process_count=1", "cp", "-r", pathglob, f"gs://{bucket.name}"]
    proc = subprocess.run(cmd, capture_output=True)

    if proc.returncode != 0:
        logging.warning(proc)
        REPORT("error", f"{tarname},load_bucket")
        return False

    # all the alerts with fixed schemas have been uploaded, so delete them from disk
    for avro in list(ALERTSDIR.glob(AVROGLOB(tarname))):
        avro.unlink()
    return True


def _bigquery_done(job):
    aglob = job.source_uris[0].split("/")[-1]  # like *.ztf_public_20221216.avro
    tarname = f"{aglob.split('.')[1]}.tar.gz"
    if job.errors is not None:
        REPORT("error", f"bqjob_{job.job_id},{aglob}")
    else:
        REPORT("done", tarname)


def load_alerts_to_table(table, tarname, bucket):
    """Load table with all alerts in bucket that correspond to tarname."""
    aglob = AVROGLOB(tarname).split("/")[-1]
    logging.info(f"Loading alerts to table. avroglob: {aglob}")
    job = BQ_CLIENT.load_table_from_uri(
        f"gs://{bucket.name}/{aglob}",
        table,
        job_config=bigquery.job.LoadJobConfig(
            write_disposition='WRITE_APPEND',
            source_format="AVRO",
            ignore_unknown_values=True,  # drop fields that are not in the table schema (cutouts)
        ),
    )
    REPORT("submitted", tarname)

    # if the job succeeds it shouldn't take very long
    # but if it fails it can take hours, so let's not wait for it.
    # this starts a helper thread to poll for the status
    job.add_done_callback(_bigquery_done)

    # job.result()
    # InternalServerError: 500 An internal error occurred and the request could not be completed. This is usually caused by a transient issue. Retrying the job with back-off as described in the BigQuery SLA should solve the problem: https://cloud.google.com/bigquery/sla. If the error continues to occur please contact support at https://cloud.google.com/support. Error: 80324028

    # if result.errors is not None:
    #     REPORT("error", f"{tarname},load_table")
    #     logging.warning(f"Error loading table for {tarname}. {result.error_result}")


def ingest_alert_to_bucket_deprecated(falert, bucket, schema, version):
    """Load one alert, fix the schema, and upload to the bucket."""
    alert_dict = open_alert(falert)
    blob = bucket.blob(
        AlertFilename(
            {
                "objectId": alert_dict["objectId"],
                "sourceId": alert_dict["candid"],
                "topic": falert.parent.name,
                "format": "avro",
            }
        ).name
    )
    blob.metadata = create_file_metadata(alert_dict)

    # fix the schema, upload, then delete the alert from disk
    # tmp = tempfile.NamedTemporaryFile()
    # with open(tmp.name, "wb") as fout:
    with tempfile.TemporaryFile() as f:
        fa.writer(f, schema, [alert_dict])
        try:
            # with open(tmp.name, "rb") as f:
            blob.upload_from_file(f, if_generation_match=0, rewind=True)
        except PreconditionFailed:  # if filename already exists in bucket. triggered by if_generation_match=0
            pass
    # tmp.close()
    # os.unlink(tmp.name)
    falert.unlink()


def download_tarball(tarname):
    """Download tarball from ZTFUTL, extract, return list of paths."""
    logging.info(f"Downloading tarball {tarname}")
    tarpath, headers = urlretrieve(f"{ZTFURL}/{tarname}", ALERTSDIR / tarname)
    adir = ALERTSDIR / tarname.replace(".tar.gz", "")
    try:
        with tarfile.open(tarpath, "r") as tar:
            tar.extractall(adir)
    except tarfile.ReadError:
        # log the error, then continue processing any alerts that were successfully extracted
        logging.warning(f"ReadError extracting tar {tarpath}")
        REPORT("error", f"{tarname},extract_tar")
    tarpath.unlink()  # delete the tarball
    return list(adir.glob("*.avro"))


def touch_schema(version, falert):
    """Check that a schema (avsc file) exists for version, creating it from falert if necessary."""
    if not schemas.FPATH(version).is_file():
        logging.info(f"Creating schema for version {version}")
        schemas.alert2avsc(falert, version=version, fixschema=True)


def touch_table(table, falert, schema_nocutouts, version):
    """Make sure the BigQuery table exists, creating it if necessary."""
    try:
        BQ_CLIENT.get_table(table)
    except NotFound:
        pass  # we'll create the table below
    else:
        return

    # easiest way to create the table using the Avro schema is to load an (Avro) alert
    # we must construct one with the fixed schema and no cutouts
    tmp = tempfile.NamedTemporaryFile()
    alert_dict = {
        k: v
        for k, v in open_alert(falert, version).items()
        if not k.startswith("cutout")
    }
    with open(tmp.name, "wb") as fout:
        fa.writer(fout, schema_nocutouts, [alert_dict])

    with open(tmp.name, "rb") as f:
        job = BQ_CLIENT.load_table_from_file(
            f,
            table,
            job_config=bigquery.job.LoadJobConfig(
                create_disposition="CREATE_IF_NEEDED",
                source_format="AVRO",
                clustering_fields=["objectId", "candid"],
                destination_table_description=f"Zwicky Transient Facility (ZTF) alerts, schema version {version}",
            )
        )
    tmp.close()
    job.result()  # TODO: check for errors
    logging.info(f"Table created: {table}")


def create_file_metadata(alert_dict):
    """Return key/value pairs to be attached to the file as metadata."""
    metadata = {
        "file_origin_message_id": f"archive_ingest_{datetime.now().timestamp()}"
    }
    metadata["objectId"] = alert_dict["objectId"]
    metadata["candid"] = alert_dict["candid"]
    metadata["ra"] = alert_dict["candidate"]["ra"]
    metadata["dec"] = alert_dict["candidate"]["dec"]
    return metadata


def guess_schema_version(alert_bytes: bytes) -> str:
    """Retrieve schema version from the Avro header."""
    version_regex_pattern = b'("version":)(\s)*(")([0-9]*\.[0-9]*)(")'
    version_match = re.search(version_regex_pattern, alert_bytes)
    if version_match is None:
        err_msg = f"Could not guess schema version for alert: {alert_bytes}"
        logger.error(err_msg)
        raise SchemaParsingError(err_msg)

    return version_match.group(4).decode()


def sayhi():
    """Test the multiproc logging."""
    with Pool(5) as pool:
        pool.map(_hi, [13, 42])


def _hi(p):
    logging.info(f'hi {p}')
    print(f'hi {p}')


def open_alert(falert, version=None):
    """Open alert from file, check that versions match, then return alert as a dict."""
    with open(falert, "rb") as fin:
        if version is not None:
            try:
                thisversion = guess_schema_version(fin.read())
            except SchemaParsingError:
                REPORT("error", f"{falert.name},unknown_version")
                return

        fin.seek(0)
        try:
            list_of_dicts = [r for r in fa.reader(fin)]
        except ValueError:
            # ValueError: expected sync marker not found
            # i think this is related to the tar not extracting properly
            REPORT("error", f"{falert.name},fa_reader_ValueError")
            logging.warning(f"Unable to deserialize alert {falert.name}")
            return

    # we expect all alerts from one tarball to have the same schema version
    # if they don't, human intervention is needed
    # and we should not proceed with processing any more alerts from this tarball
    if thisversion != version:
        REPORT("error", f"{falert.name},mismatched_versions:{thisversion}_{version}")
        raise ValueError(f"Expected alert version {version} but found {thisversion}.")

    n = len(list_of_dicts)
    if n != 1:  # this should never happen, but we'd better check
        REPORT("error", f"{falert.name},wrong_number_of_records:{n}")
        raise ValueError(f"Expected one record in alert packet but found {n}")

    return list_of_dicts[0]


def fetch_tarball_names():
    """Return list of all tarballs available from ZTFURL that we haven't already reported as "done"."""
    tardf = pd.read_html(ZTFURL)[0]
    tardf = tardf[["Name", "Size"]].dropna(how="all")
    tardf = tardf.loc[tardf['Name'].str.endswith(".tar.gz")]
    # a size of "0", "44" or "74" (bytes) means the tarball is empty
    tardf = tardf.query("Size not in ['0', '44', '74']")
    try:
        dones = pd.read_csv(FDONE, names=["Name"])
        dones = dones['Name'].to_list()
    except FileNotFoundError:
        dones = []
    return tardf.query(f"Name not in {dones}")


if __name__ == '__main__':
    # run()

    # examples for machine with 32 vcpus

    # working example
    # %%time
    tarname = "ztf_public_20221216.tar.gz"  # 1.0G
    ingest_one_tarball(tarname, nthreads=30)
    # CPU times: user 1min 59s, sys: 26.9 s, total: 2min 26s
    # Wall time: 4min 22s

    # tar extraction error example
    # %%time
    tarname = "ztf_public_20200127.tar.gz"  # 3.0G
    ingest_one_tarball(tarname, nthreads=30)

    # possible example to process multiple tarballs in parallel
    # since these vcpus are threads and not cores,
    # it might not even make sense to call Pool
    tardf = fetch_tarball_names()
    tarsample = tardf.sample(2)
    with Pool(2) as pool:
        pool.map(ingest_one_tarball, tarsample["Name"].values)
