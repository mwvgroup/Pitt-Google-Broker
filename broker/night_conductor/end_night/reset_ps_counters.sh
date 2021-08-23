#! /bin/bash
# "Reset" Pub/Sub subscriptions that function as
# counters for tracking purposes.
# Accomplished by seeking the subscription forward to current time.

PROJECT_ID=$1
testid=$2
survey="${3:-ztf}"


if [ "$testid" = "False" ]; then
    declare -a subs=(\
    "${survey}-alerts-counter" \
    "${survey}-alert_avros-counter" \
    "${survey}-alerts_pure-counter" \
    "${survey}-exgalac_trans-counter" \
    "${survey}-salt2-counter" \
    "${survey}-SuperNNova-counter" \
    )
else
    declare -a subs=(\
    "${survey}-alerts-counter-${testid}" \
    "${survey}-alert_avros-counter-${testid}" \
    "${survey}-alerts_pure-counter-${testid}" \
    "${survey}-exgalac_trans-counter-${testid}" \
    "${survey}-salt2-counter-${testid}" \
    "${survey}-SuperNNova-counter-${testid}" \
    )
fi

now=$(date)
prfx="projects/${PROJECT_ID}/subscriptions/"
for sub in ${subs[@]}; do
   gcloud pubsub subscriptions seek "${prfx}${sub}" --time="${now}"
done
