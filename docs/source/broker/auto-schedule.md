# Auto-schedule for the broker

- [Auto-scheduler](#auto-scheduler)
- [Cue-response checker](#cue-response-checker) (checks that the broker responded appropriately to the auto-scheduler's cue.)
    - [Alerting policy](#alerting-policy)

## Auto-scheduler

Broker ingestion of live topics is auto-scheduled with the following process:

__Cloud Scheduler cron job -> Pub/Sub message -> Cloud Function -> night-conductor VM startup__

The cron job sends a Pub/Sub message that simply contains either `'START'` or `'END'` (the "cue"). The Cloud Function receives this message, sets appropriate metadata attributes on the night conductor VM and starts it. When the cue is `'START'`, the Cloud Function sets the `KAFKA_TOPIC` attribute to the topic for the __current date, UTC__.

Two cron jobs are scheduled, one each to start and end the night. Both processes use the same Pub/Sub topic and Cloud Function.

Example: Change the time the broker starts each night.
```bash
survey=
testid=
jobname="${survey}-cue_night_conductor_START-${testid}"
schedule='0 2 * * *'  # UTC. unix-cron format
# https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules

gcloud scheduler jobs update pubsub $jobname --schedule "${schedule}"
```

Example: Pause/resume the broker's auto-schedule.
```bash
survey=
testid=
startjob="${survey}-cue_night_conductor_START-${testid}"
endjob="${survey}-cue_night_conductor_END-${testid}"

# pause the jobs
gcloud scheduler jobs pause $startjob
gcloud scheduler jobs pause $endjob

# resume the jobs
gcloud scheduler jobs resume $startjob
gcloud scheduler jobs resume $endjob
```

By default, the cron jobs of a Testing instance are paused immediately after creation so that the instance does not run automatically.

## Cue-response checker

The response checker Cloud Function is triggered by the auto-scheduler's Pub/Sub topic (see above). It receives the auto-scheduler's cue and then checks whether the broker responds appropriately. If the response is not as expected, "Critical" errors are raised which trigger a GCP alerting policy.

### Alerting policy

An alerting policy was created manually to notify Troy Raen of anything written to the log named `check-cue-response-cloudfnc` that has severity `'CRITICAL'`.
Every broker instance has a unique `check_cue_response` Cloud Function, but they all write to the same log.
Therefore, a new policy does not need to be created with each new broker instance.
(Also, recall that the auto-scheduler is typically only active in Production instances.)

To update the existing policy, or create a new one, see:
- [Managing log-based alerts](https://cloud.google.com/logging/docs/alerting/log-based-alerts)
- [Managing alerting policies by API](https://cloud.google.com/monitoring/alerts/using-alerting-api)
- [Managing notification channels](https://cloud.google.com/monitoring/support/notification-options)
