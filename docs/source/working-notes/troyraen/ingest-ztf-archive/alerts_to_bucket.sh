#! /bin/bash
bucket=${1}
pathglob=${2}

o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
gsutil -m -o "$o" cp -r "${pathglob}" "gs://${bucket}"
# gsutil -m cp -r "${pathglob}" "gs://${bucket}"
