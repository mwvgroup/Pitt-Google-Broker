#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import logging
import os
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from random import shuffle
from time import sleep
from urllib.request import urlretrieve

import fastavro as fa
import numpy as np
import pandas as pd
import pyarrow as pa
import schemas
from broker_utils.types import AlertFilename
from google.cloud import bigquery, storage
from google.cloud.exceptions import (
    GatewayTimeout,
    NotFound,
    PreconditionFailed,
    ServiceUnavailable,
)
from pyarrow import compute as pc
from pyarrow import csv as csv
from pyarrow import dataset as ds
from pyarrow import parquet as pq
from requests.exceptions import ReadTimeout

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

LOGSDIR = Path(__file__).parent / "logs"
LOGSDIR.mkdir(exist_ok=True)
FDONE = LOGSDIR / "done.csv"
FERR = LOGSDIR / "error.csv"
FSCHEMACHANGE = LOGSDIR / "schema-change.csv"
FSUB = LOGSDIR / "submitted-to-bigquery.csv"
FUP = LOGSDIR / "uploaded-to-bucket.csv"
FCH = LOGSDIR / "bucket-changed.csv"
FDEL = LOGSDIR / "deleted-from-bucket.csv"
ALERTSDIR = Path(__file__).parent / "alerts"
# ALERTSDIR = Path("/mnt/disks/localssd") / "alerts"  # for machines with SSD
ALERTSDIR.mkdir(exist_ok=True)
ZTFURL = "https://ztf.uw.edu/alerts/public"
PARQUET_DIR = LOGSDIR / "alerts-in-bucket.parquet"
PARQUET_DIR.mkdir(exist_ok=True)
PARQUET_DIR_CACHE = LOGSDIR / "alerts-in-bucket.cache.parquet"
PARQUET_DIR_CACHE.mkdir(exist_ok=True)

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
# DATASET = f"{SURVEY}_alerts"
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


def AVROGLOB(tarname) -> str:
    """Return glob string for .avro files with fixed schemas (relative to ALERTSDIR)."""
    tname = tarname.replace(".tar.gz", "")
    # this only matches files with fixed schemas not the original alerts extracted from the tarball
    return f"{tname}/*.{tname}.avro"


def REPORT(kind, msg):
    """Write the message to file."""
    fout = {
        "done": FDONE,
        "error": FERR,
        "submitted": FSUB,
        "uploaded": FUP,
        "moved-bucket": FCH,
        "deleted-from-bucket": FDEL,
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
    if which == "moved-bucket":
        return pd.read_csv(FCH, names=["tarstem"])["tarstem"].to_list()
    if which == "deleted-from-bucket":
        return pd.read_csv(FDEL, names=["tarstem", "bucket"])
    if which == "submitted":
        return pd.read_csv(FSUB, names=["tarname", "jobid"])

    if which == "schema-change":
        return pd.read_csv(
            FSCHEMACHANGE, names=["tarname", "version", "firstday", "lastday"]
        ).sort_values("version", ascending=False)

    if which == "parquet":
        return ds.dataset(PARQUET_DIR, partitioning="hive")


class SchemaParsingError(Exception):
    """Error parsing or guessing properties of an alert schema."""

    pass


def run():
    """Ingest all tarballs from ZTF's alert archive."""
    pass


def load_tables():
    objectds = LOAD("parquet")
    dones = LOAD("done")
    for row in LOAD("schema-change").itertuples():
        filter = ~pc.field("tarstem").isin(dones)
        filter = filter & (pc.field("tarstem") >= f"ztf_public_{row.firstday}")
        if not np.isnan(row.lastday):
            filter = filter & (pc.field("tarstem") <= f"ztf_public_{int(row.lastday)}")

        # one fragment is one night
        for frag in objectds.get_fragments(filter=filter):
            #     if i >= 83:
            #         continue
            #     change_buckets_one_night(frag, row.version, delete=delete, loadtable=loadtable)
            load_alerts_to_table_one_night(tarstem_from_parquet_path(frag.path))


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


def separate_alerts_into_versioned_buckets(delete_after_copy=True, loadtable=True):
    # assert tardf deals with a single version
    # .query(f"Name > '{mindate}'")
    objectds = LOAD("parquet")
    moved = LOAD("moved-bucket")
    # filter=(pc.field("tarstem") == tarstem)
    # schemachangedf = load("schema-change")
    # tarstems = [ts.split("/")[-2].replace("tarstem=", "") for ts in objectds.files]
    for row in LOAD("schema-change").itertuples():
        filter = ~pc.field("tarstem").isin(moved)
        filter = filter & (pc.field("tarstem") >= f"ztf_public_{row.firstday}")
        if not np.isnan(row.lastday):
            filter = filter & (pc.field("tarstem") <= f"ztf_public_{int(row.lastday)}")

        # one fragment is one night
        for frag in objectds.get_fragments(filter=filter):
            change_buckets_one_night(
                frag, row.version, delete_after_copy=delete_after_copy, loadtable=loadtable
            )


def _init_change_buckets(version, _delete_after_move=True):
    global source_bucket
    source_bucket = BUCKET(version=None, newclient=True)

    if version is not None:
        global destination_bucket
        destination_bucket = BUCKET(version=str(version), newclient=True)

    global delete_after_move
    delete_after_move = _delete_after_move


def object_datecounts_from_schemarow(row, objectds):
    filter = pc.field("tarstem") >= f"ztf_public_{row.firstday}"
    if not np.isnan(row.lastday):
        filter = filter & (pc.field("tarstem") <= f"ztf_public_{int(row.lastday)}")
    obj_tarstemcounts = pd.DataFrame(
        [
            (tarstem_from_parquet_path(frag.path), frag.metadata.num_rows)
            for frag in objectds.get_fragments(filter=filter)
        ],
        columns=["tarstem", "numrows"],
    )
    obj_tarstemcounts["date"] = (
        obj_tarstemcounts["tarstem"]
        .str.replace("ztf_public_", "")
        .str.split("_")
        .str[0]
        .astype(int)
    )
    obj_datecounts = obj_tarstemcounts[["date", "numrows"]].groupby("date").sum().squeeze()
    return obj_datecounts


def tarstem_from_parquet_path(parquetpath):
    return re.search(r"(tarstem=)(.*)/part", parquetpath).group(2)


def change_buckets_one_night(frag, version, *, npool=50, delete_after_copy=True, loadtable=True):
    tarstem = tarstem_from_parquet_path(frag.path)
    logging.info(f"changing buckets {tarstem}")
    with Pool(
        npool, initializer=_init_change_buckets, initargs=(version, delete_after_copy)
    ) as pool:
        urilist = frag.to_table()["alerturi"].to_pylist()
        # randomize the list to help avoid hotspotting
        # see https://cloud.google.com/storage/docs/request-rate
        shuffle(urilist)
        print(f"{datetime.now()} starting {tarstem} with {len(urilist)} uris")
        success = True

        for result in pool.imap_unordered(_change_buckets_one_alert, urilist, chunksize=1000):
            success = all([result, success])

    if not success:
        REPORT("error", f"{frag.path},change_buckets")
        return

    REPORT("moved-bucket", tarstem)
    if delete_after_copy:
        REPORT("deleted-from-bucket", f"{tarstem},{BUCKET(version=None, nameonly=True)}")

    if loadtable:
        load_alerts_to_table_one_night(tarstem)


def _change_buckets_one_alert(uri):
    global source_bucket
    global destination_bucket
    global delete_after_move

    current_name = uri.split("/")[-1]
    current_blob = source_bucket.blob(current_name)  # does not make a separate http request
    _, new_name = new_object_uri(uri, None, return_parts=True)

    # move it
    try:
        blob_copy = source_bucket.copy_blob(
            blob=current_blob, destination_bucket=destination_bucket, new_name=new_name
        )

    # catch some known transient errors and try again
    except (ReadTimeout, ServiceUnavailable) as e:
        print(f"sleeping 30. caught exception {e}")
        sleep(30)
        blob_copy = source_bucket.copy_blob(
            blob=current_blob, destination_bucket=destination_bucket, new_name=new_name
        )

    # if not found, assume it's already been moved and do not report an error
    except NotFound as e:
        blob_copy = None

    # catch anything that may have gone wrong. if the move didn't succeed, we need to know
    finally:
        try:
            if blob_copy is not None:
                assert blob_copy.name == new_name
        except Exception as e:
            REPORT("error", f"{uri},{e}")
            return False

    if delete_after_move:
        return _delete_from_bucket_one_alert(uri)
    return True


def delete_alerts_from_bucket():
    """Delete alerts from original bucket. Call after separate_alerts_into_versioned_buckets()."""
    objectds = ds.dataset(PARQUET_DIR, partitioning="hive")
    moved = LOAD("moved-bucket")
    deleted = LOAD("deleted-from-bucket")["tarstem"].to_list()
    moved_not_deleted = [tarstem for tarstem in moved if tarstem not in deleted]

    for row in LOAD("schema-change").itertuples():
        filter = pc.field("tarstem").isin(moved_not_deleted)
        filter = filter & (pc.field("tarstem") >= f"ztf_public_{row.firstday}")
        if not np.isnan(row.lastday):
            filter = filter & (pc.field("tarstem") <= f"ztf_public_{int(row.lastday)}")

        # one fragment is one night
        for frag in objectds.get_fragments(filter=filter):
            _delete_from_bucket_one_night(frag)
            # if i >= 83:
            #     continue
            # namelist = [uri.split("/")[-1] for uri in urilist]
            # source_bucket.delete_blobs(namelist)
    # new_name = f"{obj_name[2]}/{obj_name[0]}/{obj_name[1]}.{obj_name[3]}"


def _delete_from_bucket_one_night(frag, npool=50):
    tarstem = tarstem_from_parquet_path(frag.path)
    logging.info(f"deleting from bucket {tarstem}")
    with Pool(npool, initializer=_init_change_buckets, initargs=(None,)) as pool:
        urilist = frag.to_table()["alerturi"].to_pylist()
        print(f"{datetime.now()} starting {tarstem} with {len(urilist)} uris")
        success = True
        for result in pool.imap_unordered(_delete_from_bucket_one_alert, urilist, chunksize=1000):
            success = all([result, success])
    if success:
        REPORT("deleted-from-bucket", f"{tarstem},{BUCKET(version=None, nameonly=True)}")
    else:
        REPORT("error", f"{frag.path},delete_from_bucket")


def _delete_from_bucket_one_alert(uri):
    global source_bucket
    blob = source_bucket.blob(uri.split("/")[-1])  # does not make a separate http request

    try:
        blob.delete()

    except NotFound:
        # object doesn't exist. that's fine, let's just ~note it and~ move on
        # print("object not found " + uri)
        pass

    # catch some known transient errors and try again
    except (GatewayTimeout, ServiceUnavailable) as e:
        print(f"sleeping 30. caught exception {e}")
        sleep(30)
        # the object sometimes gets deleted on the first try, before this error gets triggered
        try:
            blob.delete()
        except NotFound:
            pass

    return True


def yyyymmdd_from_jd(jd):
    return pd.to_datetime(jd, unit="D", origin="julian").strftime("%Y%m%d")


def jd_from_yyyymmdd(yyyymmdd):
    ts = pd.Timestamp(yyyymmdd, tz=timezone.utc)
    # this is an integer mutiple of 0.5 and we need it to round away from zero, so add a little bit
    return round(ts.to_julian_date() + 1e-4)


def query_table_for_jd(version="3.3", usecache=True, convert_to_date=True):
    version = str(version)
    fcsv = LOGSDIR / f"table_counts_v{version.replace('.', '_')}.csv"
    if usecache:
        try:
            counts = pd.read_csv(fcsv).squeeze()
        except FileNotFoundError:
            pass
        else:
            if convert_to_date:
                return counts[["date", "count"]].sort_values("date").set_index("date").squeeze()
            return counts[["jd", "count"]].sort_values("jd").set_index("jd").squeeze()

    sql = (
        # cast -> int returns the closest integer value. halfway cases (0.5) round away from 0
        f"SELECT CAST(candidate.jd as INT64) as jd, COUNT(DISTINCT candid) as count "
        f"FROM `{TABLE(version=version)}` "
        f"GROUP BY jd"
    )
    query_job = BQ_CLIENT.query(sql)
    counts = query_job.result().to_dataframe()
    counts["date"] = yyyymmdd_from_jd(counts["jd"].to_numpy()).astype(int)
    counts.to_csv(fcsv)

    if convert_to_date:
        counts = counts[["date", "count"]].sort_values("date").set_index("date").squeeze()
    else:
        counts = counts[["jd", "count"]].sort_values("jd").set_index("jd").squeeze()

    return counts

    # sql = (
    #     f"SELECT candid, candidate.jd as jd "
    #     f"FROM `{PROJECT_ID}.{DATASET}.alerts` "
    #     f"WHERE candidate.jd > {jd} AND candidate.jd < {jd+1}"
    # )
    # from matplotlib import pyplot as plt
    # df = df.sort_values('jd')
    # plt.loglog(df["jd"].to_numpy(), df["candid"].to_numpy(), marker=".", linewidth=0)
    # plt.show(block=False)


def new_object_uri(old_object_uri, version, return_parts=False):
    """Return object uri with new naming syntax given object uri with old syntax."""
    # construct new name. need to turn something like this:
    # 'gs://ardent-cycling-243415-ztf-alerts/ZTF17aaaedfm.563381786215015006.ztf_public_20180718.avro'
    # into this:
    # 'gs://ardent-cycling-243415-ztf_alerts_v3_3/ztf_public_20180718/ZTF17aaaedfm/563381786215015006.avro'

    bucket = BUCKET(version, nameonly=True)
    # like ardent-cycling-243415-ztf_alerts_v3_3

    name_parts = old_object_uri.split("/")[-1].split(".")
    new_name = f"{name_parts[2]}/{name_parts[0]}/{name_parts[1]}.{name_parts[3]}"
    # like ztf_public_20180602/ZTF17aadnrzy/517454783715015049.avro

    if return_parts:
        return bucket, new_name
    return "gs://" + bucket + "/" + new_name


def load_alerts_to_table_one_night_deprecated(args):
    """Load table with all alerts in urilist."""
    tarname, objectds = args
    logging.info(f"submitting bigquery load jobs for {tarname}")

    tarstem = tarname.replace(".tar.gz", "")
    urilist = objectds.to_table(filter=(pc.field("tarstem") == tarstem))["alerturi"].to_pylist()
    # uris = [new_object_uri(uri, version) for uri in urilist]
    # aglob = AVROGLOB(tarname).split("/")[-1]
    # tbl = f"{PROJECT_ID}.{DATASET}.alerts_v{version_from_tarname(tarname).replace('.', '_')}"
    tbl = TABLE(version_from_tarname(tarname))
    job_config = bigquery.job.LoadJobConfig(
        write_disposition="WRITE_APPEND", source_format="AVRO", ignore_unknown_values=True
    )

    # need to submit in batches. load_table_from_uri has a limit of 10_000
    j, jobs, bqlim = 0, [], 10_000
    while True:
        if j * bqlim >= len(urilist):
            break

        jobs.append(
            BQ_CLIENT.load_table_from_uri(
                source_uris=urilist[j * bqlim : (j + 1) * bqlim],
                destination=tbl,
                job_config=job_config,
            )
        )
        REPORT("submitted", f"{tarname},{jobs[-1].job_id}")
        j += 1

    # if the job succeeds it shouldn't take very long
    # but if it fails it can take hours, so let's not wait for it.
    # this starts a helper thread to poll for the status
    # this causes occassional problems. let's just check on submitted jobs later
    # job.add_done_callback(_bigquery_done)

    # job.result()
    # InternalServerError: 500 An internal error occurred and the request could not be completed. This is usually caused by a transient issue. Retrying the job with back-off as described in the BigQuery SLA should solve the problem: https://cloud.google.com/bigquery/sla. If the error continues to occur please contact support at https://cloud.google.com/support. Error: 80324028

    sleep(j * 10)
    # if job.done():
    #     _bigquery_done(job)


def version_from_tarname(tarname):
    for row in LOAD("schema-change").itertuples():
        if tarname > row.tarname:
            return str(row.version)


def _run_row(row, bucket, load_table=False, nprocs=None, nthreads=None):
    tarname, tarsize = row.Name, row.Size
    logging.info(f"Starting tarball {tarname} ({tarsize})")
    logging.info("downloading")
    tarpath = download_tarball(tarname)
    logging.info("extracting")
    apaths = _extract_tarball(tarname, tarpath)
    logging.info("prepping")
    dalert, table = _prep_tarball(apaths, nprocs=nprocs)
    logging.info("loading")
    success = load_alerts_to_bucket(bucket.name, tarname, nprocs=nprocs, nthreads=nthreads)
    if success and load_table:
        load_alerts_to_table_one_night(table, tarname, bucket)
    try:
        dalert.rmdir()
    except OSError:
        REPORT("error", f"{dalert.name},rm_dir")
    logging.info(f"done with {tarname} ({tarsize})")


def extract_tarballs(queue_in, queue_out):
    """Extract tarball and return list of paths."""
    while True:
        tarname, tarpath = queue_in.get(block=True)

        if tarname == "END":
            queue_out.put(("END", "END"), block=True)
            return

        apaths = _extract_tarball(tarname, tarpath)
        logging.info(f"done with {tarname}")
        queue_out.put((tarname, apaths), block=True)


def prep_tarballs(queue_in, queue_out):
    """Target for process responsible for preping tarballs for load."""
    while True:
        tarname, apaths = queue_in.get(block=True)
        if tarname == "END":
            queue_out.put(("END", "END", "END"), block=True)
            return

        logging.info(f"starting {tarname}")
        dalert, table = _prep_tarball(apaths)
        logging.info(f"done with {tarname}")
        queue_out.put((tarname, table, dalert), block=True)


def _prep_tarball(apaths, nprocs=16):
    """Prep one tarball."""
    if nprocs is None:
        nprocs = 16
    falert = apaths[0]
    dalert = falert.parent

    with open(falert, "rb") as fin:
        version = guess_schema_version(fin.read())
    logging.info(f"alert version = {version}")

    touch_schema(version, falert)
    schema = schemas.loadavsc(version=version, nocutouts=False)

    # table = f"{PROJECT_ID}.{DATASET}.alerts_v{version.replace('.', '_')}"
    table = TABLE(version)
    touch_table(table, falert, schemas.loadavsc(version, nocutouts=True), version)

    logging.info("fixing schemas")
    with Pool(nprocs) as pool:
        pool.map(fix_alert_on_disk, [[f, schema, version] for f in apaths])

    return (dalert, table)


def load_tarballs(queue_in):
    """Target for process responsible for loading tarballs to bucket and table."""
    bucket = BUCKET()
    while True:
        tarname, table, dalert = queue_in.get(block=True)
        if tarname == "END":
            sleep(30)  # give bigquery jobs a chance to finish and report back
            return

        logging.info(f"starting {tarname}")
        _load_tarball(tarname, bucket, table, dalert)
        logging.info(f"done with {tarname}")


def _load_tarball(tarname, bucket, table, dalert):
    success = load_alerts_to_bucket(bucket.name, tarname)
    if success:
        load_alerts_to_table_one_night(table, tarname, BUCKET())

    try:
        dalert.rmdir()
    except OSError:  # directory is not empty
        REPORT("error", f"{dalert.name},rm_dir")


def ingest_one_tarball_deprecated(tarrow, nprocs=12):
    """Ingest one tarball from ZTF archive to Cloud Storage bucket and BigQuery table."""
    tarname, tarsize = tarrow
    logging.info(f"Starting tarball {tarname} ({tarsize})")
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

    table = TABLE(version)
    touch_table(table, falert, schemas.loadavsc(version, nocutouts=True), version)

    logging.info("Fixing alerts on disk")
    with Pool(nprocs) as pool:
        pool.map(fix_alert_on_disk, [[f, schema, version] for f in apaths])
    # 8: 3.5/5.9 = 0.6 min / gb
    # 12: 28/12 = 2.3 min/ gb
    # 16: 22.5/10 = 2.3 min / gb

    bucket = BUCKET()
    success = load_alerts_to_bucket(bucket, tarname)
    if success:
        load_alerts_to_table_one_night(table, tarname, bucket)

    try:
        dalert.rmdir()
    except OSError:  # directory is not empty
        REPORT("error", f"{dalert.name},rm_dir")

    logging.info(f"ingest_one_tarball done with {tarname}")


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


def load_alerts_to_bucket(bucketname, tarname, nprocs=16, nthreads=8):
    """Upload alerts to bucket. This is much simpler to batch and parallelize using `gsutil` command-line tool."""
    logging.info(f"loading to bucket {tarname}")
    # some of these tarballs get extracted with an extra directory level
    if len(list(ALERTSDIR.glob(AVROGLOB(tarname)))) > 0:
        pathglob = f"{ALERTSDIR}/{AVROGLOB(tarname)}"
    else:
        pathglob = f"{ALERTSDIR}/{tarname.replace('.tar.gz', '')}/{AVROGLOB(tarname)}"

    # gsutil:
    # -m flag runs uploads in parallel
    # macs must use multi-threading not multi-processing, specified with -o flag
    # test on GCP VM shows no time difference with and without -o flag
    if nprocs is None and nthreads is None:
        cmd = ["gsutil", "-m", "cp", "-r", pathglob, f"gs://{bucketname}"]
    else:
        multio = f"GSUtil:parallel_process_count={nprocs},parallel_thread_count={nthreads}"
        cmd = ["gsutil", "-m", f"-o {multio}", "cp", "-r", pathglob, f"gs://{bucketname}"]
    # cmd = ["gsutil", "-m", "cp", "-r", pathglob, f"gs://{bucketname}"]
    proc = subprocess.run(cmd, capture_output=True)

    if proc.returncode != 0:
        logging.warning(proc)
        REPORT("error", f"{tarname},load_bucket")
        return False

    REPORT("uploaded", tarname)

    # all the alerts with fixed schemas have been uploaded, so delete them from disk
    for avro in list(ALERTSDIR.glob(AVROGLOB(tarname))):
        avro.unlink()
    return True


def _chunk_to_parquet(chunkidx, chunk):
    partschema = pa.schema([pa.field(name="tarstem", type=pa.string())])
    objdf = pa.Table.from_batches([chunk]).to_pandas()
    objdf["tarstem"] = objdf["alerturi"].str.split(".").str[-2]

    parquet_format = ds.ParquetFileFormat()
    ds.write_dataset(
        pa.Table.from_pandas(objdf),
        base_dir=PARQUET_DIR_CACHE,
        partitioning=ds.partitioning(schema=partschema, flavor="hive"),
        basename_template=f"chunk{chunkidx}-part{{i}}.snappy.parquet",
        existing_data_behavior="overwrite_or_ignore",
        format=parquet_format,
        max_partitions=2000,  # need a few more than the default 1024
        max_open_files=2000,
        min_rows_per_group=2_000_000,
        max_rows_per_group=3_000_000,
        file_options=parquet_format.make_write_options(
            **dict(compression="snappy", version="1.0", write_statistics=False)
        ),
    )
    del objdf


def _consolidate_parquet_partition(tarstem):
    tardir = PARQUET_DIR_CACHE / f"tarstem={tarstem}"
    if not tardir.is_dir():
        return

    meta_collect = []

    def file_visitor(written_file):
        meta_collect.append(written_file.metadata)

    # read everything in this directory
    tbl = pq.read_table(tardir)
    # we loose the partition column by reading this way. add it back in.
    partfield = pa.field(name="tarstem", type=pa.string())
    tbl = tbl.append_column(field_=partfield, column=[[tarstem] * len(tbl)])

    parquet_format = ds.ParquetFileFormat()
    ds.write_dataset(
        tbl,
        base_dir=PARQUET_DIR,
        partitioning=ds.partitioning(schema=pa.schema([partfield]), flavor="hive"),
        basename_template=f"part{{i}}.snappy.parquet",
        file_options=parquet_format.make_write_options(
            **dict(compression="snappy", version="1.0", write_statistics=False)
        ),
        format=parquet_format,
        existing_data_behavior="overwrite_or_ignore",
        file_visitor=file_visitor,
        min_rows_per_group=3_000_000,
        max_rows_per_group=4_000_000,
    )

    return meta_collect


def _consolidate_parquet():
    # previous step creates large number of small files.
    # next line take a very long time (several hours). don't do it this way. iterate dir instead.
    # dataset = ds.dataset(PARQUET_DIR_CACHE, partitioning="hive")
    tardf = fetch_tarball_names(clean=[])
    tarstems = tardf["Name"].str.replace(".tar.gz", "").to_list()
    with Pool(12) as pool:
        pool.map(_consolidate_parquet_partition, tarstems)


def object_csv_to_parquet(csvin):
    # csvin can be obtained by running the following in a bash shell:
    # gsutil ls gs://${bucket} > csvin
    with csv.open_csv(
        csvin,
        read_options=csv.ReadOptions(column_names=["alerturi"], block_size=1024 ** 2),
        convert_options=csv.ConvertOptions(
            column_types=pa.schema([pa.field(name="alerturi", type=pa.string())])
        ),
    ) as reader:
        for chunkidx, chunk in enumerate(reader):
            _chunk_to_parquet(chunkidx, chunk)

    _consolidate_parquet()


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


def create_file_metadata(alert_dict):
    """Return key/value pairs to be attached to the file as metadata."""
    metadata = {"file_origin_message_id": f"archive_ingest_{datetime.now().timestamp()}"}
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
    logging.info(f"hi {p}")
    print(f"hi {p}")


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
            # trigger PreconditionFailed if filename already exists in bucket with if_generation_match=0
            blob.upload_from_file(f, if_generation_match=0, rewind=True)
        except PreconditionFailed:
            pass
    # tmp.close()
    # os.unlink(tmp.name)
    falert.unlink()


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


def _bigquery_done_deprecated(job):
    aglob = job.source_uris[0].split("/")[-1]  # like *.ztf_public_20221216.avro
    tarname = f"{aglob.split('.')[1]}.tar.gz"
    if job.errors is not None:
        REPORT(
            "error", f"{aglob.replace('*.', '').replace('.avro', '.tar.gz')},bqjob_{job.job_id}"
        )
    else:
        REPORT("done", tarname)


def _bigquery_done(jobs):
    aglob = job.source_uris[0].split("/")[-1]  # like *.ztf_public_20221216.avro
    tarname = f"{aglob.split('.')[1]}.tar.gz"
    if job.errors is not None:
        REPORT(
            "error", f"{aglob.replace('*.', '').replace('.avro', '.tar.gz')},bqjob_{job.job_id}"
        )
    else:
        REPORT("done", tarname)


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

    return tardf.query(f"Name not in {reported}").sort_values("Name").reset_index()


if __name__ == "__main__":
    # run()
    pass
