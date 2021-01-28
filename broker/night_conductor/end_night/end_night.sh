#! /bin/bash
# Stop all VM instances, Beam/Dataflow jobs, and other resources
# related to running the nightly broker

testid=$1

# stop the ztf-consumer VM instance
./stop_consumer.sh $testid

# wait a few minutes for ztf-consumer to shutdown
# then stop/drain the Dataflow jobs
sleep 120
./drain_beam_jobs.sh
