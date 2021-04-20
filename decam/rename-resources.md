# Rename resources

The following resources were renamed to accommodate an arbitrary survey name (prepended to the resource name):

- BQ datasets:
    - `ztf_alerts` -> `{survey}_alerts`
- Cloud Storage:
    - `{PROJECT_ID}-broker_files` -> `{PROJECT_ID}-{survey}-broker_files`
    - `{PROJECT_ID}_dataflow` -> `{PROJECT_ID}-{survey}-dataflow`
    - `{PROJECT_ID}_testing_bucket` -> `{PROJECT_ID}-{survey}-testing_bucket`
    - `{PROJECT_ID}_ztf_alert_avros` -> `{PROJECT_ID}-{survey}-alert_avros`
    - `{PROJECT_ID}_ztf-sncosmo` -> `{PROJECT_ID}-{survey}-sncosmo`
- Compute Engine instances:
    - `night-conductor` -> `{survey}-night-conductor`
    - `ztf-consumer` -> `{survey}-consumer`
- Dataflow:
    - `bq-sink` -> `{survey}-bq-sink`
    - `value-added` -> `{survey}-value-added`
- Pub/Sub:
    - `ztf_alert_avros` -> `{survey}-alert_avros`
    - `ztf_alert_avros-counter` -> `{survey}-alert_avros-counter`
    - `ztf_alerts` -> `{survey}-alerts`
    - `ztf_alerts-counter` -> `{survey}-alerts-counter`
    - `ztf_alerts-reservoir` -> `{survey}-alerts-reservoir`
    - `ztf_alerts_pure` -> `{survey}-alerts_pure`
    - `ztf_alerts_pure-counter` -> `{survey}-alerts_pure-counter`
    - `ztf_exgalac_trans` -> `{survey}-exgalac_trans`
    - `ztf_exgalac_trans-counter` -> `{survey}-exgalac_trans-counter`
    - `ztf_salt2` -> `{survey}-salt2`
    - `ztf_salt2-counter` -> `{survey}-salt2-counter`
