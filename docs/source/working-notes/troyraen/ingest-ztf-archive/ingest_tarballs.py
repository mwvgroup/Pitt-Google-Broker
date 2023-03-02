#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import logging
import os
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime
from multiprocessing import Pool, Process, Queue
from pathlib import Path
from time import sleep
from urllib.request import urlretrieve

import fastavro as fa
import pandas as pd
import pyarrow as pa
import schemas
from broker_utils.types import AlertFilename
from google.cloud import bigquery, storage
from google.cloud.exceptions import NotFound, PreconditionFailed
from pyarrow import compute as pac
from pyarrow import csv as pacsv
from pyarrow import dataset as pads


PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

LOGSDIR = Path(__file__).parent / "logs"
LOGSDIR.mkdir(exist_ok=True)
FDONE = LOGSDIR / "done.csv"
FERR = LOGSDIR / "error.csv"
FSCHEMACHANGE = LOGSDIR / "schema-change.csv"
SCHEMA_CHANGE_DF = pd.read_csv(FSCHEMACHANGE, names=["tarname", "version"]).sort_values(
    "version", ascending=False
)
FSUB = LOGSDIR / "submitted-to-bigquery.csv"
FUP = LOGSDIR / "uploaded-to-bucket.csv"
ALERTSDIR = Path(__file__).parent / "alerts"
# ALERTSDIR = Path("/mnt/disks/localssd") / "alerts"  # for machines with SSD
ALERTSDIR.mkdir(exist_ok=True)
ZTFURL = "https://ztf.uw.edu/alerts/public"
PARQUET_DIR = LOGSDIR / "alerts-in-bucket.parquet"
PARQUET_DIR.mkdir(exist_ok=True)

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
DATASET = f"{SURVEY}_alerts"
_BUCKET = f"{PROJECT_ID}-{SURVEY}-alerts"
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
    fout = {"done": FDONE, "error": FERR, "submitted": FSUB, "uploaded": FUP}
    with open(fout[kind], "a") as f:
        f.write(f"{msg}\n")


class SchemaParsingError(Exception):
    """Error parsing or guessing properties of an alert schema."""

    pass


def run():
    """Ingest all tarballs from ZTF's alert archive."""
    # tardf = fetch_tarball_names()
    # i = 0
    # sampdf = tardf.sort_index(ascending=False).iloc[i*10:(i+5)*10]

    # nprocs = 8. ntarballs = 10. 33.5 GB
    #  - CPU times: user 15min 55s, sys: 5min 57s, total: 21min 53s
    #  - Wall time: 3h 44min 3s
    # nprocs = 16. ntarballs = 10. 40.1 GB
    # - CPU times: user 12min 20s, sys: 4min 36s, total: 16min 57s
    # - Wall time: 2h 25min 12s
    # i, nprocs = 0, 16
    # sampdf = tardf.sort_index(ascending=False).iloc[i*10:(i+5)*10]
    # # print(sum([float(s.strip('MG')) for s in sampdf['Size']]))
    # for row in sampdf.itertuples():
    #     ingest_one_tarball((row.Name, row.Size), nprocs=nprocs)
    #
    # i, nprocs = 0, 16
    # logging.info(f"nprocs = {nprocs}")
    # sampdf = tardf.sort_index(ascending=False).iloc[i*10:(i+2)*10]
    # print(sum([float(s.strip('G')) for s in sampdf['Size']]))
    # # downloads take forever
    # with Pool(2) as pool:
    #     pool.map(ingest_one_tarball, [(r.Name, r.Size) for r in sampdf.itertuples()])
    # # 20 tarballs. 77.3 GB

    # 36: 8
    # 96: 8
    # 08: 16
    # 86: 12
    # 10: 20

    # # QUEUEs
    # # 171 GB in about 24 hours
    # extract_queue, prep_queue, load_queue = Queue(3), Queue(2), Queue(2)
    #
    # extract_proc = Process(target=extract_tarballs, args=(extract_queue, prep_queue), name="ExtractTarballs")
    # prep_proc = Process(target=prep_tarballs, args=(prep_queue, load_queue), name="PrepTarballs")
    # load_proc = Process(target=load_tarballs, args=(load_queue,), name="LoadTarballs")
    # procs = [extract_proc, prep_proc, load_proc]
    #
    # for proc in procs:
    #     proc.start()
    #
    # for row in sampdf.itertuples():
    #     tarname, tarsize = row.Name, row.Size
    #     logging.info(f"Starting tarball {tarname} ({tarsize})")
    #     tarpath = download_tarball(tarname)
    #     extract_queue.put((tarname, tarpath), block=True)
    # extract_queue.put(("END", "END"))
    #
    # for proc in procs:
    #     proc.join()
    #     proc.close()

    # SERIAL - load to bucket
    tardf = it.fetch_tarball_names()
    # bigdf = tardf.query("SizeG >= 25").sort_index(ascending=False)
    # lastog = 'ztf_public_20190220.tar.gz'
    # sampdf = tardf.query("Name > @lastog").sort_index(ascending=False)
    df19idx = tardf["Name"].str.strip("ztf_public_").str.startswith("2019")  # big
    df19 = tardf.loc[df19idx].sort_index(ascending=False)
    df20idx = tardf["Name"].str.strip("ztf_public_").str.startswith("2020")  # 2020
    df20 = tardf.loc[df20idx].query("SizeG < 25").sort_index(ascending=False)
    df21idx = tardf["Name"].str.strip("ztf_public_").str.startswith("2021")  # big
    df21 = tardf.loc[df21idx].query("SizeG < 25").sort_index(ascending=False)
    df22idx = tardf["Name"].str.strip("ztf_public_").str.startswith("2022")  # 2020
    df22 = tardf.loc[df22idx].query("SizeG < 25").sort_index(ascending=False)
    df23idx = tardf["Name"].str.strip("ztf_public_").str.startswith("2023")  # big
    df23 = tardf.loc[df23idx].sort_index(ascending=False)
    bucket = it.BUCKET()

    for row in df23.iloc[:10].itertuples():
        it._run_row(row, bucket, load_table=False)
        # run_row(row, 16, 1)

    # ztf_public_20210108

    # ingest - 11471 - ztf_public_20200224 - mydf = df20.iloc[45:100].query('SizeG < 25') - 55
    # double - 11700 - ztf_public_20200712 - mydf = df20.iloc[136:200].query('SizeG < 25') - 62
    # triple - 16255 - ztf_public_20201012 - mydf = df20.iloc[220:].query('SizeG < 25') - 67

    # ---- original machine
    # 307 GB
    # CPU times: user 1h 32min 46s, sys: 36min 32s, total: 2h 9min 18s
    # Wall time: 23h 35min 57s

    # ---- bigdf
    # 244 GB in 12h 25m
    # 246 GB in 12h 38m
    # 234 GB in 12h 11m
    # 551 GB in 1d 4h
    # 562 GB in 1d 3h
    # before resizing to 32 cpu 48G ram:
    # 258 GB in 18h 15m
    # 368 GB in 1d 4m
    # 377 GB in 1d 50m
    #
    # df25 = bigdf.query('SizeG == 25')
    #
    # row = df25.iloc[0]
    # ztf_public_20181114.tar.gz 25G with nproc = 16
    # CPU times: user 7min, sys: 2min 30s, total: 9min 31s
    # Wall time: 1h 6min 15s
    #
    # row = df25.iloc[1]
    # ztf_public_20200821.tar.gz 25G with nproc = 32
    # Wall time: 1h 7min
    #
    # row = df25.iloc[2]
    # ztf_public_20201019.tar.gz 25G with nproc = 8
    # CPU times: user 7min 12s, sys: 2min 28s, total: 9min 41s
    # Wall time: 1h 8min 12s
    #
    # ztf_public_20210210.tar.gz 26G with nprocs = 16, nthreads=8
    # CPU times: user 7min 12s, sys: 2min 28s, total: 9min 40s
    # Wall time: 1h 7min 42s
    #
    # bigdf.iloc[:6] 257G
    # CPU times: user 1h 14min 1s, sys: 25min 38s, total: 1h 39min 40s
    # Wall time: 11h 32min 42s

    # load to table
    # get list of objects in bucket by running the following in a bash shell:
    # gsutil ls gs://${bucket} > alerts-in-bucket.txt
    it.object_csv_to_parquet(csvin=it.LOGSDIR / "alerts-in-bucket.txt.gz")
    objectds = pads.dataset(it.PARQUET_DIR, partitioning="hive")
    tardf = it.fetch_tarball_names(clean=["done"])
    for row in tardf.itertuples():
        tarname = row.Name
        it.load_alerts_to_table((tarname, objectds))
        #     table=f"{it.PROJECT_ID}.{it.DATASET}.alerts_v{it.version_from_tarname(tarname).replace('.', '_')}",
        #     tarname=tarname,
        #     urilist=objectds.to_table(
        #         filter=(pac.field("tarstem") == tarname.replace(".tar.gz", ""))
        #     )["alerturi"].to_pylist(),
        # )
    # try to parallelize
    with Pool(4) as pool:
        pool.map(load_alerts_to_table, [(tarname, objectds) for tarname in tardf["Name"].values])


# def load_alerts_to_table(table, tarname, bucket):
# def load_alerts_to_table(table, tarname, urilist):
def load_alerts_to_table(args):
    """Load table with all alerts in urilist."""
    tarname, objectds = args
    tarstem = tarname.replace(".tar.gz", "")
    urilist = objectds.to_table(filter=(pac.field("tarstem") == tarstem))["alerturi"].to_pylist()
    # aglob = AVROGLOB(tarname).split("/")[-1]
    logging.info(f"submitting bigquery load job {tarname}")
    job = BQ_CLIENT.load_table_from_uri(
        # glob string load jobs fail after awhile (too many objects in bucket?).
        # f"gs://{bucket.name}/{aglob}",
        # pass explicit list of uris instead
        urilist,
        table=f"{PROJECT_ID}.{DATASET}.alerts_v{version_from_tarname(tarname).replace('.', '_')}",
        job_config=bigquery.job.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            source_format="AVRO",
            ignore_unknown_values=True,  # drop fields that are not in the table schema (cutouts)
        ),
    )
    REPORT("submitted", f"{tarname},{job.job_id}")

    # if the job succeeds it shouldn't take very long
    # but if it fails it can take hours, so let's not wait for it.
    # this starts a helper thread to poll for the status
    # this causes occassional problems. let's just check on submitted jobs later
    # job.add_done_callback(_bigquery_done)

    # job.result()
    # InternalServerError: 500 An internal error occurred and the request could not be completed. This is usually caused by a transient issue. Retrying the job with back-off as described in the BigQuery SLA should solve the problem: https://cloud.google.com/bigquery/sla. If the error continues to occur please contact support at https://cloud.google.com/support. Error: 80324028

    # if result.errors is not None:
    #     REPORT("error", f"{tarname},load_table")
    #     logging.warning(f"Error loading table for {tarname}. {result.error_result}")

    sleep(60)
    if job.done():
        _bigquery_done(job)


def version_from_tarname(tarname):
    for row in SCHEMA_CHANGE_DF.itertuples():
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
        load_alerts_to_table(table, tarname, bucket)
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

    table = f"{PROJECT_ID}.{DATASET}.alerts_v{version.replace('.', '_')}"
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
        load_alerts_to_table(table, tarname, BUCKET())

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

    table = f"{PROJECT_ID}.{DATASET}.alerts_v{version.replace('.', '_')}"
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
        load_alerts_to_table(table, tarname, bucket)

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

    parquet_format = pads.ParquetFileFormat()
    pads.write_dataset(
        pa.Table.from_pandas(objdf),
        base_dir=PARQUET_DIR,
        partitioning=pads.partitioning(schema=partschema, flavor="hive"),
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


def object_csv_to_parquet(csvin):
    # csvin can be obtained by running the following in a bash shell:
    # gsutil ls gs://${bucket} > csvin
    with pacsv.open_csv(
        csvin,
        read_options=pacsv.ReadOptions(column_names=["alerturi"], block_size=1024 ** 3),
        convert_options=pacsv.ConvertOptions(
            column_types=pa.schema([pa.field(name="alerturi", type=pa.string())])
        ),
    ) as reader:
        for chunkidx, chunk in enumerate(reader):
            _chunk_to_parquet(chunkidx, chunk)


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


def _bigquery_done(job):
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
        subdf = pd.read_csv(FSUB, names=["tarname", "jobid"])
    except FileNotFoundError:
        return

    # remove tarballs previously reported as done
    try:
        dones = list(pd.read_csv(FDONE, names=["tarname"]).squeeze())
    except FileNotFoundError:
        dones = []
    subdf = subdf.query("tarname not in @dones")

    # remove jobids previously reported as errored
    try:
        errs = pd.read_csv(FERR, names=["tarname", "error"])["error"]
        errs = list(errs.loc[errs.str.startswith("bqjob_")].str.replace("bqjob_", ""))
    except FileNotFoundError:
        errs = []
    subdf = subdf.query("jobid not in @errs")

    # check and report on remaining jobs
    for row in subdf.itertuples():
        job = BQ_CLIENT.get_job(row.jobid)
        if job.done():
            _bigquery_done(job)


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
            uploaded = pd.read_csv(FUP, names=["tarname"])["tarname"].to_list()
        except FileNotFoundError:
            uploaded = []
        reported = list(set(uploaded + reported))

    if "submitted" in clean:
        try:
            submitted = pd.read_csv(FSUB, names=["tarname", "jobid"])["tarname"].to_list()
        except FileNotFoundError:
            submitted = []
        reported = list(set(submitted + reported))

    if "done" in clean:
        try:
            dones = pd.read_csv(FDONE, names=["tarname"])["tarname"].to_list()
        except FileNotFoundError:
            dones = []
        reported = list(set(dones + reported))

    return tardf.query(f"Name not in {reported}")


if __name__ == "__main__":
    # run()
    pass
