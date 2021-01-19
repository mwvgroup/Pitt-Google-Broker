#! /bin/bash
# Stop all VM instances, Beam/Dataflow jobs, and other resources
# related to running the nightly broker

# stop the ztf-consumer VM instance
./stop_consumer.sh

# wait a few minutes for ztf-consumer to shutdown
# then stop/drain the Dataflow jobs
sleep 2m
./drain_beam_jobs.sh
