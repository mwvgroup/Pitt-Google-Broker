#! /bin/bash
# Stop all VM instances, Beam/Dataflow jobs, and other resources
# related to running the nightly broker

PROJECT_ID=$1
testid=$2
survey="${3:-ztf}"

#--- Stop the ztf-consumer VM instance
echo
echo "Stopping Consumer instance..."
./stop_consumer.sh "$testid" "$survey"

#--- Drain the Dataflow jobs
echo
echo "Waiting 2 min to give processes related to Consumer time to settle down..."
sleep 120
echo "Draining Dataflow jobs..."
./drain_beam_jobs.sh "$PROJECT_ID"  # waits for status = "Drained" or "Cancelled"

#--- Process Pub/Sub counters
echo
echo "Waiting 2 min so Pub/Sub counters have time to register the plateau..."
sleep 120
echo "Processing Pub/Sub counters..."
if [ "$testid" = "False" ]; then
    python3 process_pubsub_counters.py --survey="$survey" --production
else
    python3 process_pubsub_counters.py --survey="$survey" --testid="$testid"
fi
