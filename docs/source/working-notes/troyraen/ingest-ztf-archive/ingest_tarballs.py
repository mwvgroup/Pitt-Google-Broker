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
    """Return glob string for .avro files."""
    tname = tarname.replace(".tar.gz", "")
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
    # with multiproc:
    with Pool(3) as pool:
        pool.map(ingest_one_tarball, tardf["Name"].values)
    # for tarname in tardf["Name"]:
    #     ingest_one_tarball(tarname)
    # dirname = "ztf_public_20180601"
    # dirname = "ztf_public_20230121"


def ingest_one_tarball(tarname):
    """Ingest one tarball from ZTF archive."""
    logging.info(f"Starting tarball {tarname}")
    apaths = download_tarball(tarname)
    try:
        falert = apaths[0]
        dalert = falert.parent
    except IndexError:
        return

    with open(falert, "rb") as fin:
        version = guess_schema_version(fin.read())
    logging.info(f"Alert version = {version}")

    touch_schema(version, falert)
    schema = schemas.loadavsc(version=version, nocutouts=False)

    table = f"{PROJECT_ID}.{DATASET}.alerts_v{version.replace('.', '_')}"
    touch_table(table, falert, schemas.loadavsc(version, nocutouts=True), version)

    logging.info("Fixing alerts on disk")
    with ThreadPool(32) as pool:
        pool.map(fix_alert_on_disk, [[f, schema, version] for f in apaths])
    # logging.info("Loading alerts to bucket")
    # for falert in apaths:
    #     try:
    #         ingest_alert_to_bucket(falert, bucket, schema, version)
    #     except Timeout:
    #         logging.warning("Reconnecting to bucket due to timeout.")
    #         sleep(5)
    #         bucket = BUCKET()
    #         ingest_alert_to_bucket(falert, bucket, schema, version)

    bucket = BUCKET()
    success = load_alerts_to_bucket(bucket, tarname)
    if success:
        load_alerts_to_table(table, tarname, bucket)

    try:
        dalert.rmdir()
    except OSError:  # directory is not empty
        REPORT("error", f"{dalert.name},rm_dir")

    REPORT("done", tarname)
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

    # fix the schema, write a new file, then delete the original alert from disk
    with open(fout, "wb") as f:
        fa.writer(f, schema, [alert_dict])
    falert.unlink()


def load_alerts_to_bucket(bucket, tarname, disable_multiproc_for_mac=False):
    """Upload alerts to bucket. This is much simpler to batch and parallelize using `gsutil` command-line tool."""
    logging.info(f"Loading alerts to bucket. {tarname}")

    # pathglob = f"{ALERTSDIR}/{AVROGLOB(tarname)}"
    # if disable_multiproc_for_mac:
    #     # must disable multiprocessing with -o to run this on a mac
    #     cmd = f"gsutil -m -o GSUtil:parallel_process_count=1 cp -r {pathglob} gs://{bucket.name}"
    # else:
    #     cmd = f"gsutil -m cp -r {pathglob} gs://{bucket}"
    # proc = subprocess.run(cmd, capture_output=True)
    proc = subprocess.run(
        [Path(__file__).resolve().parent / "alerts_to_bucket.sh", bucket.name, f"{ALERTSDIR}/{AVROGLOB(tarname)}"],
        # cwd=paths.dout(),
        capture_output=True,
    )
    if proc.returncode != 0:
        logging.warning(proc)
        REPORT("error", f"{tarname},load_bucket")
        return False

    for avro in list(ALERTSDIR.glob(AVROGLOB(tarname))):
        avro.unlink()
    return True


def load_alerts_to_table(table, tarname, bucket):
    """Load table with all alerts in bucket that correspond to tarname."""
    # targlob = f"*.{tarname.replace('.tar.gz', '')}.avro"
    aglob = AVROGLOB(tarname).split("/")[-1]
    logging.info(f"Loading alerts to table. avroglob: {aglob}")
    job = BQ_CLIENT.load_table_from_uri(
        f"gs://{bucket.name}/{aglob}",
        table,
        job_config=bigquery.job.LoadJobConfig(
            write_disposition='WRITE_APPEND',
            source_format="AVRO",
            ignore_unknown_values=True,  # drop fields that are not in the table schema (schema_uri)
        ),
    )
    result = job.result()
    # InternalServerError: 500 An internal error occurred and the request could not be completed. This is usually caused by a transient issue. Retrying the job with back-off as described in the BigQuery SLA should solve the problem: https://cloud.google.com/bigquery/sla. If the error continues to occur please contact support at https://cloud.google.com/support. Error: 80324028
    if result.errors is not None:
        REPORT("error", f"{tarname},load_table")
        logging.warning(f"Error loading table for {tarname}. {result.error_result}")


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
    apaths = [p.resolve() for p in adir.glob("*.avro")]
    return apaths


def touch_schema(version, falert):
    """Check that a schema (avsc file) exists for version, creating it from falert if necessary."""
    spath = schemas.fpath(version)
    # schema_uri = f"{bucket.name}/{spath.name}"
    if not spath.is_file():
        logging.info(f"Creating schema for version {version}")
        # create the fixed schema dn upload to bucket
        schemas.alert2avsc(falert, version=version, fixschema=True)
        # blob = bucket.blob(spath.name)
        # with open(spath, "rb") as f:
        #     blob.upload_from_file(f)
    # parsed_schema = fa.parse_schema(schemas.loadavsc(version=version, nocutouts=False))


def touch_table(table, falert, schema_nocutouts, version):
    """Make sure the BigQuery table exists, creating it if necessary."""
    try:
        BQ_CLIENT.get_table(table)
        logging.debug(f"Table exists {table}")
    except NotFound:
        alert_dict = {
            k: v
            for k, v in open_alert(falert, version).items()
            if not k.startswith("cutout")
        }
        tmp = tempfile.NamedTemporaryFile()
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
        job.result()
        logging.info(f"Table created: {table}")

    # with open(spath.replace())


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

    if thisversion != version:
        REPORT("error", f"{falert.name},mismatched_versions:{thisversion}_{version}")
        raise ValueError(f"Expected alert version {version} but found {thisversion}.")

    n = len(list_of_dicts)
    if n != 1:
        REPORT("error", f"{falert.name},too_many_records:{n}")
        raise ValueError(f"Expected one record in alert packet but found {n}")

    return list_of_dicts[0]


def fetch_tarball_names():
    """Download list of all available tarballs to csv."""
    tardf = pd.read_html(ZTFURL)[0]
    # a size of "44" or "74" (bytes) means the tarball is empty
    tardf = tardf[["Name", "Size"]].dropna(how="all").query("Size not in ['0', '44', '74']")
    tardf = tardf.loc[tardf['Name'].str.endswith(".tar.gz")]
    try:
        dones = pd.read_csv(FDONE, names=["Name"])
        dones = dones['Name'].to_list()
    except FileNotFoundError:
        dones = []
    return tardf.query(f"Name not in {dones}")


if __name__ == '__main__':
    run()
