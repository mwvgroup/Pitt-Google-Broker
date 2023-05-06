# Ingest ZTF Archive

The [ZTF archive](https://ztf.uw.edu/alerts/public) was ingested into the "ztf_alerts_v*" buckets and tables in early 2023.
The following files contain the working notes and code that were used:

- [working_notes.py](working_notes.py)
- [ingest_tarballs_working_version.py](ingest_tarballs_working_version.py)
- [setup.sh](setup.sh)

A cleaned-up version of the code that can be used in the future is at:

- [ingest_tarballs.py](ingest_tarballs.py)
- [setup.sh](setup.sh)

## Instructions

1. Setup a VM to use for the ingestion ([setup.sh](setup.sh))
2. Setup other GCP resources like buckets and tables if needed ([setup.sh](setup.sh))
3. Ingest tarballs ([ingest_tarballs.py](ingest_tarballs.py)). Basic usage:

```python
import ingest_tarballs as it

it.run(tardf=it.fetch_tarball_names(clean=["done"]))
```

This does the following:

- load list of tarballs available from [ZTF archive](https://ztf.uw.edu/alerts/public) cleaned of any that have already been logged as done
- ingest all tarballs, one at a time:
    - download and extract the tarball
    - fix the avro schemas to conform to bigquery's strict standards (parallelized)
    - upload the alerts (avro files) to the bucket (parallelized)
    - load the alerts to the table
- write logs to logs/ingest_tarballs.log and create other files in the logs directory to keep track of what's completed thru various stages

Some steps are parallelized.
Defaults should work reasonably well on the SSD machine created in setup.sh.
In addition, a single machine can probably do a few `it.run()` in parallel using (e.g.,) `screen` and submitting slices of `tardf` to each `run` call.
