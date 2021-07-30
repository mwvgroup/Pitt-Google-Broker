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

#--- Reset Pub/Sub counters
echo
echo "Waiting 2 min so Pub/Sub counters have time to register the plateau..."
sleep 120
echo "Resetting Pub/Sub counters..."
./reset_ps_counters.sh "$PROJECT_ID" "$testid" "$survey"
