#! /bin/bash
# Stop all VM instances, Beam/Dataflow jobs, and other resources
# related to running the nightly broker

PROJECT_ID=$1
testid=$2

#--- Stop the ztf-consumer VM instance
echo
echo "Stopping Consumer instance..."
./stop_consumer.sh $testid

#--- Drain the Dataflow jobs
echo
echo "Waiting to give processes related to Consumer time to settle down..."
sleep 120
echo "Draining Dataflow jobs..."
./drain_beam_jobs.sh ${PROJECT_ID}  # script waits for status = "Drained"

#--- Reset Pub/Sub counters
echo
echo "Waiting so Pub/Sub counters have time to register the plateau..."
sleep 120
echo "Resetting Pub/Sub counters..."
./reset_ps_counters.sh ${PROJECT_ID} ${testid}
