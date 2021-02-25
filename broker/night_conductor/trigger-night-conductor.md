- [Cloud Scheduler] Define a schedule on which Pub/Sub messages will be published
- [Pub/Sub]
- [Cloud Function] `trigger_night_conductor`: listens to a PS topic, sets metadata on `night-conductor`, starts `night-conductor`
    - (basically, run `run-conduct.sh` but need to re-write in python)


- [Scheduling compute instances with Cloud Scheduler](https://cloud.google.com/scheduler/docs/start-and-stop-compute-engine-instances-on-a-schedule)
    - replace their CF with our own
- [Python Examples for Cloud Function]
    - [Set Metadata](https://cloud.google.com/compute/docs/reference/rest/v1/instances/setMetadata#examples)
    - [Start Instance](https://cloud.google.com/compute/docs/reference/rest/v1/instances/start#examples)
