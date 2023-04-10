#! /bin/bash
# Creates or deletes the Cloud Scheduler cron jobs
# This script will not delete jobs that are in production


testid="${1:-test}"
#   "False" uses production resources
#   any other string will be appended to the names of all resources
teardown="${2:-False}" # "True" tearsdown/deletes resources, else setup
survey="${3:-ztf}"
# name of the survey this broker instance will ingest
region="${4:-us-central1}"

#--- GCP resources used in this script
# "cue_night_conductor" is a misnomer. "broker_admin" would be more appropriatiate.
# but these are Pub/Sub topics and Scheduler cron jobs (global resources),
# so leaving for now...
cue_night_conductor="${survey}-cue_night_conductor"
night_conductor_START="${survey}-cue_night_conductor_START"
night_conductor_END="${survey}-cue_night_conductor_END"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    cue_night_conductor="${cue_night_conductor}-${testid}"
    night_conductor_START="${night_conductor_START}-${testid}"
    night_conductor_END="${night_conductor_END}-${testid}"
fi

#--- Teardown resources
if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud scheduler jobs delete "$night_conductor_START" --location "$region"
        gcloud scheduler jobs delete "$night_conductor_END" --location "$region"
    fi

#--- Create cron jobs
else
    timezone='UTC'  # to avoid daylight savings issues
    scheduleSTART='00 2 * * *'  # START at 2:00am UTC / 6:00pm PDT, everyday
    scheduleEND='05 16 * * *'  # END at 4:05pm UTC / 9:05am PDT, everyday
    msgSTART='START'
    msgEND='END'

    gcloud scheduler jobs create pubsub $night_conductor_START \
        --schedule "${scheduleSTART}" \
        --topic $cue_night_conductor \
        --message-body $msgSTART \
        --time-zone $timezone \
        --location "$region"

    gcloud scheduler jobs create pubsub $night_conductor_END \
        --schedule "${scheduleEND}" \
        --topic $cue_night_conductor \
        --message-body $msgEND \
        --time-zone $timezone \
        --location "$region"

    # Tell the user the schedule and how to change it
    echo
    echo "The 'cue night-conductor' cron jobs have been scheduled for:"
    echo "START: ${scheduleSTART}"
    echo "END: ${scheduleEND}"
    echo "(timezone is ${timezone})"
    echo "To change this use"
    echo
    echo "gcloud scheduler jobs update pubsub $night_conductor_START --schedule '* * * * *' --location $region"
    echo "gcloud scheduler jobs update pubsub $night_conductor_END --schedule '* * * * *' --location $region"
    echo
    echo "where '* * * * *' is a schedule in unix-cron format."
    echo "See https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules"


    # if this is a testing instance, pause the jobs and tell the user how to resume
    if [ "$testid" != "False" ]; then
        gcloud scheduler jobs pause "$night_conductor_START" --location "$region"
        gcloud scheduler jobs pause "$night_conductor_END" --location "$region"

        echo
        echo "The 'cue night-conductor' cron jobs have been placed in the 'pause' state."
        echo "To resume them, run"
        echo
        echo "gcloud scheduler jobs resume $night_conductor_START --location $region"
        echo "gcloud scheduler jobs resume $night_conductor_END --location $region"
        echo
    fi

fi
