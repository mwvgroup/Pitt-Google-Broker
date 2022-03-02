# Night Conductor

See the broker-level [../README.md](../README.md) for instructions on setting up a
broker instance.

- [`gcloud compute instances create`](https://cloud.google.com/sdk/gcloud/reference/compute/instances/create)
- [Startup scripts](https://cloud.google.com/compute/docs/startupscript)
- [Storing and retrieving instance metadata](https://cloud.google.com/compute/docs/storing-retrieving-metadata)
  - [Setting custom metadata](https://cloud.google.com/compute/docs/storing-retrieving-metadata#custom)
- [Filtering and formatting fun with `gcloud`](https://cloud.google.com/blog/products/gcp/filtering-and-formatting-fun-with)

## Auto-schedule

The broker is auto-scheduled with a process that looks like this:

Cloud Scheduler cron job -> Pub/Sub -> Cloud Function -> Night Conductor VM startup

- [Scheduling compute instances with Cloud Scheduler](https://cloud.google.com/scheduler/docs/start-and-stop-compute-engine-instances-on-a-schedule)
