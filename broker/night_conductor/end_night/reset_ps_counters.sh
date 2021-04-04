#! /bin/bash
# "Reset" Pub/Sub subscriptions that function as
# counters for tracking purposes.
# Accomplished by seeking the subscription forward to current time.

PROJECT_ID=$1
testid=$2

if [ "$testid" = "False" ]; then
    declare -a subs=(\
    "ztf_alerts-counter" \
    "ztf_alert_avro_bucket-counter" \
    "ztf_exgalac_trans-counter" \
    "ztf_salt2-counter" \
    )
else
    declare -a subs=(\
    "ztf_alerts-counter-${testid}" \
    "ztf_alert_avro_bucket-counter-${testid}" \
    "ztf_exgalac_trans-counter-${testid}" \
    "ztf_salt2-counter-${testid}" \
    )
fi

now=$(date)
prfx="projects/${PROJECT_ID}/subscriptions/"
for sub in ${subs[@]}; do
   gcloud pubsub subscriptions seek "${prfx}${sub}" --time="${now}"
done
