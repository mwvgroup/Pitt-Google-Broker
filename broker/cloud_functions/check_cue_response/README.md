# Check cue response

This Cloud Function checks whether the broker responded appropriately to the
auto-scheduler's cue. It does this by first pausing to allow time for the response, and
then checking each broker component, such as VMs and Dataflow jobs. If a component is
found to be in an unexpected state, a "Critical" error is raised which triggers a GCP
alerting policy.

This Cloud Function is triggered by the auto-scheduler's Pub/Sub topic. For reference,
the auto-scheduling process looks like this (see [Auto-scheduler](auto-scheduler.md)):

Cloud Scheduler cron job -> Pub/Sub -> Cloud Function -> Night Conductor VM startup

## Alerting policy

An alerting policy was created manually to notify Troy Raen of anything written to the
log named `check-cue-response-cloudfnc` that has severity `'CRITICAL'`. Every broker
instance has a unique `check_cue_response` Cloud Function, but they all write to the
same log. Therefore, a new policy does not need to be created with each new broker
instance. (Also, recall that the auto-scheduler is typically only active in Production
instances.)

To update the existing policy, or create a new one, see:

- [Managing log-based alerts](https://cloud.google.com/logging/docs/alerting/log-based-alerts)
- [Managing alerting policies by API](https://cloud.google.com/monitoring/alerts/using-alerting-api)
- [Managing notification channels](https://cloud.google.com/monitoring/support/notification-options)

## Links

- [`googleapiclient.discovery.build` Library reference documentation by API](https://github.com/googleapis/google-api-python-client/blob/master/docs/dyn/index.md)
