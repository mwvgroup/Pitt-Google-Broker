"""Ingest all tarballs from ZTF's alert archive."""
from datetime import datetime, timezone
from multiprocessing import Pool

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from google.cloud import bigquery
from google.cloud.exceptions import TooManyRequests
from time import sleep

import ingest_tarballs_working_version as it

# region ---- start
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
# endregion

# region ---- QUEUEs ---- did not work
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
# endregion

# region ---- SERIAL - load to bucket
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

# endregion

# region ---- load to table
# get list of objects in bucket by running the following in a bash shell:
# gsutil ls gs://${bucket} > alerts-in-bucket.txt
# do this once:
# it.object_csv_to_parquet(csvin=it.LOGSDIR / "alerts-in-bucket.txt.gz")
objectds = ds.dataset(it.PARQUET_DIR, partitioning="hive")
tardf = it.fetch_tarball_names(clean=["done"])
for row in tardf.itertuples():
    tarname = row.Name
    it.load_alerts_to_table_one_night((tarname, objectds))

# try to parallelize. this works fine, but there's a quota that limits how many per day
with Pool(4) as pool:
    pool.map(
        it.load_alerts_to_table_one_night,
        [(tarname, objectds) for tarname in tardf["Name"].values],
    )

# nearly all data thru 1/1/2021 has been loaded, but the quota makes this is painful
# most of the rest of it is already in the current alerts table,
# so load 1/2/2021 -> present by querying the current alerts table
# 1/2/2021 -> julian date = 2459216.5
query_job = it.BQ_CLIENT.query(
    f"SELECT * FROM `{it.PROJECT_ID}.{it.DATASET}.alerts` where candidate.jd > 2459216.5",
    job_config=bigquery.job.QueryJobConfig(
        destination=f"{it.PROJECT_ID}.{it.DATASET}.alerts_v3_3", write_disposition="WRITE_APPEND"
    ),
)
# query_job.done()
it.check_submitted_jobs()
# that worked very well. quick and painless.
# endregion

# region ---- check what's in the table vs the bucket
# if the results here are to be believed, there's
# about 285 missing nights and 425 nights where num rows in table != num alerts in bucket
objectds = ds.dataset(it.PARQUET_DIR, partitioning="hive")
tardf = it.fetch_tarball_names(clean=["done"])
dones = it.LOAD("done")
version = "3.3"
numbqrows = it.query_table_for_jd(version, usecache=True)
mindate = it.LOAD("schema-change").query(f"version == {version}")["tarname"].squeeze()

notequal, nightmissing = [], []
for row in tardf.query(f"Name > '{mindate}'").itertuples():
    tarstem = row.Name.replace(".tar.gz", "")

    # count rows (alerts/uris) that match the tarname
    frags = objectds.get_fragments(filter=(pc.field("tarstem") == tarstem))
    numobjects = sum([pq.read_metadata(frag.path).num_rows for frag in frags])

    # get jd for this tarstem
    ts = pd.Timestamp(tarstem.replace("ztf_public_", "").split("_")[0], tz=timezone.utc)
    # this is an integer mutiple of 0.5 and we need it to round away from zero, so add a little bit
    jd = round(ts.to_julian_date() + 1e-4)

    try:
        if not numbqrows[jd] == numobjects:
            # print(tarstem, numbqrows[jd], numobjects)
            notequal.append(tarstem)
    except KeyError:
        # print("no alerts in table for " + tarstem)
        nightmissing.append(tarstem)
    # urilist = objectds.to_table(filter=(pc.field("tarstem") == tarstem))["alerturi"].to_pylist()

# endregion

# region ---- separate alerts into versioned buckets
it.separate_alerts_into_versioned_buckets()
it.delete_alerts_from_bucket()

# this took 1 minute with 100_000 objects in bucket, crashed with 4mil in the bucket
# it used gs://{bucket}/*
# it.create_table_from_bucket(version="1.8")
# endregion

# region ---- check what made it from ZTF archive all the way to table
# check which tarballs are in the bucket vs ztf's archive
tardf = it.fetch_tarball_names(clean=[])
ztftarstems = tardf["Name"].str.replace(".tar.gz", "").to_list()
ztftarstems.sort()

objectds = it.LOAD("parquet")
objtarstems = set(it.tarstem_from_parquet_path(frag.path) for frag in objectds.get_fragments())
objtarstems = list(objtarstems)
objtarstems.sort()

not_ingested = [tarstem for tarstem in ztftarstems if tarstem not in objtarstems]

# check total number of alerts per date that are in the table vs the bucket
for row in it.LOAD("schema-change").itertuples():
    version = row.version
    obj_datecounts = it.object_datecounts_from_schemarow(row, objectds)
    row_datecounts = it.query_table_for_jd(version=version, usecache=True, convert_to_date=True)
    inbucket_nottable = obj_datecounts.subtract(row_datecounts)
    # ~if everything was loaded to table correctly this should sum to 0~
    # nans get in the way
    print(inbucket_nottable.sum())

# load bucket -> table if not already done
date = "20190418"
it.load_alerts_to_table_one_night((f"ztf_public_{date}"))
# endregion

# region ---- v3.3 move, delete, load
# create table
# doesn't work with bucket and dataset in different locations
# randomv33uri = "gs://ardent-cycling-243415-ztf-alerts/ZTF17aaaaaal.1380386795815015014.ztf_public_20201012.avro"
# load_job = it.BQ_CLIENT.load_table_from_uri(
#     source_uris=randomv33uri,
#     destination=it.TABLE("3.3", nameonly=True),
#     job_config=bigquery.job.LoadJobConfig(
#         write_disposition="WRITE_APPEND", source_format="AVRO", ignore_unknown_values=True
#     ),
# )

# remove submitted-to-bigquery.csv to start fresh!
# clean done.csv to remove v3.3

# move, delete, load
objectds = it.LOAD("parquet")
moved = it.LOAD("moved-bucket")
scdf = it.LOAD("schema-change")
row = scdf.iloc[0]
filter = ~pc.field("tarstem").isin(moved) & (pc.field("tarstem") >= f"ztf_public_{row.firstday}")
# 9 parallel screens worked ok
# but, wait 30 min between starting each screen to give cloud storage time to scale
# https://cloud.google.com/storage/docs/request-rate
numscreens, screen = 3, 0
numfrags_perscreen = sum(1 for _ in objectds.get_fragments(filter=filter)) // numscreens
npool = 24
for i, frag in enumerate(objectds.get_fragments(filter=filter)):
    if (i < screen * numfrags_perscreen) or (i >= (screen + 1) * numfrags_perscreen):
        continue
    try:
        it.change_buckets_one_night(
            frag, row.version, delete_after_copy=True, loadtable=False, npool=npool
        )
    # if we get stopped for hotspotting, move on to the next night. will have to come back later
    except TooManyRequests as e:
        print(f"sleeping 15. caught exception {e}")
        sleep(15)

    # print(frag.path)
# endregion

# region ---- ingest the last few days
import ingest_tarballs as it  # use the cleaned-up version
import pandas as pd

# do once. afterwards, load from logs/not-ingested.txt
# get list of tarstems that still need to be ingested
scdf = it.LOAD("schema-change")
# logs/bucket-folders.txt was copy-pasted from the gcp console
folders = pd.read_csv("logs/bucket-folders.txt", names=["topic"]).squeeze()
tardf = it.fetch_tarball_names(clean=[])
ztfv3 = tardf.query('Name > "ztf_public_20190618.tar.gz"')["Name"].str.replace(".tar.gz", "")
notingested = set(ztfv3) - set(folders)
# tarstems are "ztf_public_yyyymmdd" while topics are "ztf_yyyymmdd_programid1"
# manually remove these dates, then manually save the list to logs/not-ingested.txt
folders[folders.str.endswith("programid1")]

# get tardf of dates that need to be ingested
notingested = pd.read_csv("logs/not-ingested.txt", names=["tarstem"])
notingested["tarname"] = notingested["tarstem"] + ".tar.gz"
tardf = it.fetch_tarball_names(clean=["done", "uploaded"])
tardf = tardf.query(f"Name in {notingested['tarname'].to_list()}")

it.run(tardf=tardf, load_table=False)
# endregion

# region ---- check what's in the table vs the archive. load table from bucket.
import ingest_tarballs as it
from ingest_tarballs_working_version import query_table_for_jd

tardf = it.fetch_tarball_names(clean=[])
tardf["date"] = (
    tardf["Name"].str.strip("ztf_public_").str.strip(".tar.gz").str.replace("_programid3", "")
)
tardf = tardf.astype({"date": int})

scdf = it.LOAD("schema-change")
for row in scdf.itertuples():
    # ztf_dates = tardf.query(f"date >= {row.firstday} and date <= {row.lastday}")["date"].to_list()
    ztf_dates = tardf.query(f"date >= {row.firstday}")["date"].to_list()
    row_datecounts = query_table_for_jd(version=row.version, usecache=True, convert_to_date=True)
    row_dates = row_datecounts.index.to_list()
    missing = set(ztf_dates) - set(row_dates)
    print(missing)

# v3.3 still has holes
for date in missing:
    tarstem = f"ztf_public_{date}"
    it.load_alerts_to_table_one_night(tarstem)

# big query bugged out. won't load unless schema matches exactly. can't load alerts containing cutouts
# endregion

# region ---- create full v3.3 table from bucket
import pandas as pd
import re
import shlex
import subprocess
from multiprocessing import Pool
from google.api_core import page_iterator
from random import sample

import ingest_tarballs as it
from ingest_tarballs_working_version import jd_from_yyyymmdd, yyyymmdd_from_jd

version = "3.3"
bucket = it.BUCKET(version)
# table_name = it.TABLE(version, nameonly=True)
table_name = "alerts_v3_3_fullschema"
table_id = f"{it.PROJECT_ID}.{it.DATASET}.{table_name}"

# create new table including cutout fields
schema = f"schemas/bq_ztf_alerts_v3_3_fullschema.json"
bqmk = f"bq mk --table {it.PROJECT_ID}:{it.DATASET}.{table_name} {schema}"
out = subprocess.check_output(shlex.split(bqmk))
print(f"{out}")  # should be a success message

# fetch all bucket prefixes. no way to do this directly with the client/bucket
# workaround found in this issue: https://github.com/googleapis/python-storage/issues/294
# which is itself adapted from https://stackoverflow.com/a/59008580
prefix_iter = page_iterator.HTTPIterator(
    client=bucket.client,
    api_request=bucket.client._connection.api_request,
    path=f"/b/{bucket.name}/o",
    items_key="prefixes",
    item_to_value=lambda iterator, item: item,
    extra_params={
        # "projection": "noAcl",
        "prefix": "",
        "delimiter": "/",
        "userProject": bucket.client.project,
    },
)
prefixes = [pre for pre in prefix_iter]


# load table
def load_table(prefix):
    bucket_name = "ardent-cycling-243415-ztf_alerts_v3_3"
    table_name = "alerts_v3_3_fullschema"
    table_id = f"{it.PROJECT_ID}.{it.DATASET}.{table_name}"

    load_job = it.load_table_from_bucket(
        table_name=table_id,
        source_uris=f"gs://{bucket_name}/{prefix}*",
        reportid=prefix,
    )
    load_job.result()  # wait for the job to finish

    return prefix


npool = 8
with Pool(npool) as pool:  # 6hrs
    for result in pool.imap_unordered(load_table, prefixes, chunksize=100):
        print(result)


# check submitted jobs
def job_completed_successfully(subdf_row):
    job = it.BQ_CLIENT.get_job(subdf_row.jobid, location="us-central1")
    return job.done() and (job.errors is None)


subdf = it.LOAD("submitted")
subdf["success"] = subdf.apply(job_completed_successfully, axis=1)

all(subdf.success)  # True
set(prefixes) - set(subdf.tarname)  # empty set
# looks good

# check the table
# count rows in table
sql = (
    # cast -> int returns the closest integer value. halfway cases (0.5) round away from 0
    f"SELECT CAST(candidate.jd as INT64) as jd, COUNT(candid) as count "
    f"FROM `{table_id}` "
    f"GROUP BY jd"
)
query_job = it.BQ_CLIENT.query(sql)
counts = query_job.result().to_dataframe()
counts["date"] = yyyymmdd_from_jd(counts["jd"].to_numpy()).astype(int)
counts.to_csv(it.LOGSDIR / f"table_counts_{table_name}.csv")  # save for later
counts = counts.set_index("date").sort_index()

# check for duplicates
query_job = it.BQ_CLIENT.query(sql.replace("COUNT(candid)", "COUNT(DISTINCT candid)"))
distinctcounts = query_job.result().to_dataframe()
distinctcounts["date"] = yyyymmdd_from_jd(distinctcounts["jd"].to_numpy()).astype(int)
distinctcounts = distinctcounts.set_index("date").sort_index()
distinctcounts.equals(counts)  # True. no duplicates

len(prefixes) == len(counts.index)  # False. i think there are some nights with multiple tarnames

prefixes = pd.DataFrame({"prefix": prefixes})
prefixes["date"] = prefixes.apply(
    lambda row: int(re.search("[0-9]{8}", row.prefix).group()), axis=1
)
len(prefixes.date.unique()) == len(counts.index)  # True

# spot check number of objects in a prefix
# update: this is killing this small vm. not cpu or memory. i think it's throughput and iops.
# i checked about 3 and they were fine.
objectcount = []
for prefix in sample(list(prefixes.prefix), 10):
    objectcount.append((prefix, len(list(bucket.list_blobs(prefix=prefix)))))
objectcount = pd.DataFrame(objectcount, columns=["prefix", "numobjects"])
objectcount["date"] = objectcount.apply(
    lambda row: int(re.search("[0-9]{8}", row.prefix).group()), axis=1
)
for ocrow in objectcount.itertuples():
    if len(prefixes.query(f"date == {ocrow.date}").index) != 1:
        print("date has >1 prefix", ocrow)
    assert ocrow.numobjects == counts.loc[counts["date"] == ocrow.date, "count"].squeeze()

# clean up and move table

# move/rename existing table
# cant rename because of recent streaming operations
# try copy and delete
ogtable_id = table_id.removesuffix("_fullschema")
job = it.BQ_CLIENT.copy_table(ogtable_id, ogtable_id + "_og")
it.BQ_CLIENT.delete_table(ogtable_id)

# drop cutout columns
for cutout in ["cutoutScience", "cutoutTemplate", "cutoutDifference"]:
    sql = f"ALTER TABLE {table_id} DROP COLUMN {cutout}"
    job = it.BQ_CLIENT.query(sql)

# rename table
sql = f"ALTER TABLE {table_id} RENAME TO {ogtable_id.split('.')[-1]}"
job = it.BQ_CLIENT.query(sql)

# endregion

# region ---- check stats on final table
import pandas as pd
import re
from google.api_core import page_iterator
from random import sample

import ingest_tarballs as it
from ingest_tarballs_working_version import jd_from_yyyymmdd, yyyymmdd_from_jd

version = "3.3"
bucket = it.BUCKET(version)
table_name = "alerts_v3_3"
table_id = f"{it.PROJECT_ID}.{it.DATASET}.{table_name}"

# count rows in table per date
sql = (
    # cast -> int returns the closest integer value. halfway cases (0.5) round away from 0
    f"SELECT CAST(candidate.jd as INT64) as jd, COUNT(candid) as count "
    f"FROM `{table_id}` "
    f"GROUP BY jd"
)
query_job = it.BQ_CLIENT.query(sql)
counts = query_job.result().to_dataframe()
counts["date"] = yyyymmdd_from_jd(counts["jd"].to_numpy()).astype(int)
counts.to_csv(it.LOGSDIR / f"table_counts_{table_name}.csv")  # save for later
counts = counts.set_index("date").sort_index()

# check for duplicates
query_job = it.BQ_CLIENT.query(sql.replace("COUNT(candid)", "COUNT(DISTINCT candid)"))
distinctcounts = query_job.result().to_dataframe()
distinctcounts["date"] = yyyymmdd_from_jd(distinctcounts["jd"].to_numpy()).astype(int)
distinctcounts = distinctcounts.set_index("date").sort_index()
distinctcounts.equals(counts)  # True. no duplicates

# compare number of days in bucket vs in table
# get bucket prefixes
prefix_iter = page_iterator.HTTPIterator(
    client=bucket.client,
    api_request=bucket.client._connection.api_request,
    path=f"/b/{bucket.name}/o",
    items_key="prefixes",
    item_to_value=lambda iterator, item: item,
    extra_params={
        # "projection": "noAcl",
        "prefix": "",
        "delimiter": "/",
        "userProject": bucket.client.project,
    },
)
prefixes = [pre for pre in prefix_iter]
prefixes = pd.DataFrame({"prefix": prefixes})
prefixes["date"] = prefixes.apply(
    lambda row: int(re.search("[0-9]{8}", row.prefix).group()), axis=1
)
len(prefixes.date.unique()) == len(counts.index)  # True

# endregion

# region ---- scratch
jd = it.jd_from_yyyymmdd(date)
sql = (
    # cast -> int returns the closest integer value. halfway cases (0.5) round away from 0
    f"SELECT CAST(candidate.jd as INT64) as jd, COUNT(DISTINCT candid) as count "
    f"FROM `{it.TABLE(version=version)}` "
    f"WHERE CAST(candidate.jd as INT64) = {jd} "
    f"GROUP BY jd"
)
query_job = it.BQ_CLIENT.query(sql)
counts = query_job.result().to_dataframe()
# endregion
