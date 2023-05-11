#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import logging
import os
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path
from urllib.request import urlretrieve

import fastavro as fa
import pandas as pd
import schemas
from broker_utils.types import AlertFilename
from google.cloud import bigquery, storage
from google.cloud.exceptions import NotFound

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")
NUMCPUS = os.cpu_count()

LOGSDIR = Path(__file__).parent / "logs"
LOGSDIR.mkdir(exist_ok=True)
FDONE = LOGSDIR / "done.csv"
FERR = LOGSDIR / "error.csv"
FSCHEMACHANGE = LOGSDIR / "schema-change.csv"
FSUB = LOGSDIR / "submitted-to-bigquery.csv"
FUP = LOGSDIR / "uploaded-to-bucket.csv"
# ALERTSDIR = Path(__file__).parent / "alerts"  # for machines without SSD
ALERTSDIR = Path("/mnt/disks/localssd") / "alerts"  # for machines with SSD
ALERTSDIR.mkdir(exist_ok=True)
ZTFURL = "https://ztf.uw.edu/alerts/public"

handler = logging.FileHandler(LOGSDIR / "ingest_tarballs.log")
handler.setLevel(logging.INFO)
handler.setFormatter(
    logging.Formatter(
        "[%(levelname)s] %(name)s: %(asctime)s [%(process)d:%(processName)s] %(message)s"
    )
)
logger = logging.getLogger()
logger.addHandler(handler)

BQ_CLIENT = bigquery.Client()
STORAGE_CLIENT = storage.Client()
DATASET = SURVEY
_BUCKET = f"{PROJECT_ID}-{SURVEY}-alerts"
if TESTID != "False":
    DATASET = f"{DATASET}_{TESTID}"
    _BUCKET = f"{_BUCKET}-{TESTID}"
_TABLE = f"{PROJECT_ID}.{DATASET}.alerts"


def BUCKET(version=None, nameonly=False, newclient=False):
    """Connect to the bucket and return it."""
    client = storage.Client() if newclient else STORAGE_CLIENT

    if version is None:
        if nameonly:
            return _BUCKET
        return client.get_bucket(client.bucket(_BUCKET, user_project=PROJECT_ID))

    if TESTID != "False":
        raise NotImplementedError("versioned bucket names not implemented for TESTID != False")

    bucket = _BUCKET.replace("ztf-alerts", "ztf_alerts") + f"_v{version.replace('.', '_')}"
    if nameonly:
        return bucket
    return client.get_bucket(client.bucket(bucket, user_project=PROJECT_ID))


def TABLE(version=None, nameonly=True):
    """Return the name of the table."""
    if not nameonly:
        raise NotImplementedError("fetching the table is not implemented here")
    if version is None:
        return _TABLE
    return f"{_TABLE}_v{version.replace('.', '_')}"


# def AVROGLOB(tarname) -> str:
#     """Return glob string for .avro files with fixed schemas (relative to ALERTSDIR)."""
#     tname = tarname.replace(".tar.gz", "")
#     # this only matches files with fixed schemas not the original alerts extracted from the tarball
#     return f"{tname}/{tname}/**.avro"


def REPORT(kind, msg):
    """Write the message to file."""
    fout = {
        "done": FDONE,
        "error": FERR,
        "submitted": FSUB,
        "uploaded": FUP,
    }
    with open(fout[kind], "a") as f:
        f.write(f"{msg}\n")


def LOAD(which="done"):
    if which == "done":
        return pd.read_csv(FDONE, names=["tarname"])["tarname"].to_list()
    if which == "error":
        return pd.read_csv(FERR, names=["tarname", "error"])
    if which == "uploaded":
        return pd.read_csv(FUP, names=["tarname"])["tarname"].to_list()
    if which == "submitted":
        return pd.read_csv(FSUB, names=["tarname", "jobid"])

    if which == "schema-change":
        return pd.read_csv(
            FSCHEMACHANGE, names=["tarname", "version", "firstday", "lastday"]
        ).sort_values("version", ascending=False)


class SchemaParsingError(Exception):
    """Error parsing or guessing properties of an alert schema."""

    pass


def load_alerts_to_table_one_night(tarstem):
    logging.info(f"submitting bigquery load jobs for {tarstem}")
    version = version_from_tarname(tarstem + ".tar.gz")
    # urilist = objectds.to_table(filter=(pc.field("tarstem") == tarstem))["alerturi"].to_pylist()
    load_job = BQ_CLIENT.load_table_from_uri(
        source_uris="gs://" + BUCKET(version, nameonly=True) + "/" + tarstem + "/*",
        destination=TABLE(version, nameonly=True),
        job_config=bigquery.job.LoadJobConfig(
            write_disposition="WRITE_APPEND", source_format="AVRO", ignore_unknown_values=True
        ),
    )
    # load_job.done()
    REPORT("submitted", f"{tarstem}.tar.gz,{load_job.job_id}")


def version_from_tarname(tarname):
    for row in LOAD("schema-change").itertuples():
        if tarname >= row.tarname:
            return str(row.version)


def _prep_one_night(apaths, nprocs=NUMCPUS // 2):
    """Prep one night. Touch table. Fix schema of every alert in `apaths`."""
    if nprocs is None:
        nprocs = 16
    falert = apaths[0]

    with open(falert, "rb") as fin:
        version = guess_schema_version(fin.read())
    logging.info(f"alert version = {version}")

    touch_schema(version, falert)
    schema = schemas.loadavsc(version=version, nocutouts=False)

    # table = f"{PROJECT_ID}.{DATASET}.alerts_v{version.replace('.', '_')}"
    table = TABLE(version)
    touch_table(table, falert, schemas.loadavsc(version, nocutouts=True), version)

    logging.info("fixing schemas")
    with Pool(nprocs) as pool:  # 25 sec with nprocs=16 and len(apaths) = 160,000
        # this is a long iterable, so use imap with a big chunksize
        argsgen = ([f, schema, version] for f in apaths)
        for _ in pool.imap_unordered(fix_alert_on_disk, argsgen, chunksize=1000):
            continue

    return table


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
    fout.parent.mkdir(exist_ok=True, parents=True)
    with open(fout, "wb") as f:
        fa.writer(f, schema, [alert_dict])
    falert.unlink()


def load_alerts_to_bucket(bucketname, tarname, nprocs=NUMCPUS):
    """Upload alerts to bucket. This is much simpler to batch and parallelize using `gsutil` command-line tool."""
    logging.info(f"loading to bucket {tarname}")
    tarstem = tarname.replace(".tar.gz", "")
    tardir = ALERTSDIR / tarstem / tarstem

    if nprocs is None:
        cmd = ["gsutil", "-m", "-u", PROJECT_ID, "cp", "-r", f"{tardir}", f"gs://{bucketname}"]
    else:
        cmd = [
            "gsutil",
            "-m",
            f"-o GSUtil:parallel_process_count={nprocs}",
            "-u",
            PROJECT_ID,
            "cp",
            "-r",
            f"{tardir}",
            f"gs://{bucketname}",
        ]
    proc = subprocess.run(cmd, capture_output=True)

    if proc.returncode != 0:
        logging.warning(proc)
        REPORT("error", f"{tarname},load_bucket")
        return False

    REPORT("uploaded", tarname)

    # all the alerts with fixed schemas have been uploaded, so delete them from disk
    # for avro in list(ALERTSDIR.glob(AVROGLOB(tarname))):
    for objdir in tardir.iterdir():
        for avro in objdir.iterdir():
            avro.unlink()
        objdir.rmdir()
    tardir.rmdir()
    tardir.parent.rmdir()

    return True


def _extract_tarball(tarname, tarpath):
    adir = ALERTSDIR / tarname.replace(".tar.gz", "")
    try:
        with tarfile.open(tarpath, "r") as tar:
            tar.extractall(adir)
    except tarfile.ReadError:
        # log the error, then continue processing any alerts that were successfully extracted
        logging.warning(f"ReadError extracting tar {tarpath}")
        REPORT("error", f"{tarname},extract_tar_ReadError")
    except PermissionError:
        logging.warning(f"PermissionError extracting tar {tarpath}")
        REPORT("error", f"{tarname},extract_tar_PermissionError")

    tarpath.unlink()  # delete the tarball
    apaths = list(adir.glob("*.avro"))
    # some of these tarballs get extracted with an extra directory level
    if len(apaths) == 0:
        apaths = list((adir / tarname.replace(".tar.gz", "")).glob("*.avro"))
    return apaths


def download_tarball(tarname):
    """Download tarball from ZTFUTL."""
    # logging.info(f"Downloading tarball {tarname}")
    tarpath, headers = urlretrieve(f"{ZTFURL}/{tarname}", ALERTSDIR / tarname)
    # logging.info(f"download_tarball done with {tarname}")
    return tarpath


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
        k: v for k, v in open_alert(falert, version).items() if not k.startswith("cutout")
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
            ),
        )
    tmp.close()
    job.result()  # TODO: check for errors
    logging.info(f"Table created: {table}")


def guess_schema_version(alert_bytes: bytes) -> str:
    """Retrieve schema version from the Avro header."""
    version_regex_pattern = b'("version":)(\s)*(")([0-9]*\.[0-9]*)(")'
    version_match = re.search(version_regex_pattern, alert_bytes)
    if version_match is None:
        err_msg = f"Could not guess schema version for alert: {alert_bytes}"
        logger.error(err_msg)
        raise SchemaParsingError(err_msg)

    return version_match.group(4).decode()


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


def check_submitted_jobs():
    """Check jobs submitted to BigQuery and update the done report."""
    logging.info("checking status of BigQuery jobs")

    # get submitted jobs
    try:
        subdf = LOAD("submitted")
    except FileNotFoundError:
        return

    # remove tarballs previously reported as done
    try:
        dones = LOAD("done")
    except FileNotFoundError:
        dones = []
    subdf = subdf.query("tarname not in @dones")

    # remove jobids previously reported as errored
    try:
        errs = LOAD("error")["error"]
        errs = list(errs.loc[errs.str.startswith("bqjob_")].str.replace("bqjob_", ""))
    except FileNotFoundError:
        errs = []
    subdf = subdf.query("jobid not in @errs")

    # check and report on remaining jobs
    for tarname, jobsdf in subdf.groupby("tarname"):
        _check_bigquery_jobs(tarname, jobsdf)


def _check_bigquery_jobs(tarname, jobsdf):
    """Check all jobs in jobsdf. Report tarname as done if all jobs completed without error."""
    jobs = [BQ_CLIENT.get_job(row.jobid) for row in jobsdf.itertuples()]

    # if any jobs is not done, just return
    if any([(not job.done()) for job in jobs]):
        return

    if any([job.errors for job in jobs]):
        print(f"{tarname} errors: {[job.errors for job in jobs]}")
        return

    # all jobs succeeded
    REPORT("done", tarname)


def _convert_tarsize(size):
    num = float(size.strip("KMG"))
    if size.endswith("G"):
        return num
    if size.endswith("M"):
        return num / 1024
    if size.endswith("K"):
        return num / 1024 / 2014


def fetch_tarball_names(clean=["uploaded", "submitted"]):
    """Return list of all tarballs available from ZTFURL that we haven't already reported as "done"."""
    tardf = pd.read_html(ZTFURL)[0]
    # clean it up
    tardf = tardf[["Name", "Size"]].dropna(how="all")
    tardf["SizeG"] = tardf["Size"].apply(_convert_tarsize)
    tardf = tardf.loc[tardf["Name"].str.endswith(".tar.gz"), :]
    # if size is in bytes, the tarball is empty and SizeG is NaN
    tardf = tardf.dropna(subset=["SizeG"])

    # clean as requested
    reported = []
    if "uploaded" in clean:
        try:
            uploaded = LOAD("uploaded")
        except FileNotFoundError:
            uploaded = []
        reported = list(set(uploaded + reported))

    if "submitted" in clean:
        try:
            submitted = LOAD("submitted")["tarname"].to_list()
        except FileNotFoundError:
            submitted = []
        reported = list(set(submitted + reported))

    if "done" in clean:
        try:
            dones = LOAD("done")
        except FileNotFoundError:
            dones = []
        reported = list(set(dones + reported))

    return tardf.query(f"Name not in {reported}").sort_values("Name").reset_index(drop=True)


def run_one_night(tardf_row, *, bucket, load_table=True, nprocs=NUMCPUS * 3 // 4):
    tarname, tarsize = tardf_row.Name, tardf_row.Size
    logging.info(f"Starting tarball {tarname} ({tarsize})")

    logging.info("downloading")
    tarpath = download_tarball(tarname)  # 2 min for 7GB

    logging.info("extracting")
    apaths = _extract_tarball(tarname, tarpath)  # 1.5 min for 7GB

    logging.info("prepping")
    table = _prep_one_night(apaths, nprocs=nprocs)  # 30 sec for 7GB (160,000 alerts)

    logging.info("loading")
    success = load_alerts_to_bucket(bucket.name, tarname, nprocs=nprocs * 2)
    if success and load_table:
        load_alerts_to_table_one_night(table, tarname, bucket)

    logging.info(f"done with {tarname} ({tarsize})")


def run(tardf=None, load_table=True, nprocs=NUMCPUS * 3 // 4):
    """Ingest all tarballs from ZTF's alert archive."""
    if tardf is None:
        tardf = fetch_tarball_names()

    for row in tardf.itertuples():
        bucket = BUCKET(version=version_from_tarname(row.Name))
        run_one_night(row, bucket=bucket, load_table=load_table, nprocs=nprocs)
