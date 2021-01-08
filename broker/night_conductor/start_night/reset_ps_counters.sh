#! /bin/bash
# "Reset" Pub/Sub subscriptions that function as counters for
# tracking purposes.
# Accomplished by seeking the subscription forward to current time.

PROJECT_ID=$1
now=$(date)
prfx="projects/${PROJECT_ID}/subscriptions/"
declare -a subs=(\
"ztf_alert_data-counter" \
"ztf_alert_avro_bucket-counter" \
"ztf_exgalac_trans-counter" \
"ztf_salt2-counter" \
)
for sub in ${subs[@]}; do
   gcloud pubsub subscriptions seek "${prfx}${sub}" --time="${now}"
done
