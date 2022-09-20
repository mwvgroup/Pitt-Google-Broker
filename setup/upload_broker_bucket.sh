#! /bin/bash

broker_bucket=$1 # name of GCS bucket where broker files should be staged

echo
echo "Uploading broker files to GCS..."
o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
gsutil -m -o "$o" cp -r ../consumer "gs://${broker_bucket}"
gsutil -m -o "$o" cp -r ../setup_broker "gs://${broker_bucket}"
