#! /bin/bash
# Create BigQuery tables using the schema from existing tables

PROJECT_ID=$1
testid=$2

if [ "$testid" != "False" ]; then

    # create a table for the alert data
    oldtable="ztf_alerts.alerts"
    newtable="ztf_alerts_${testid}.alerts"
    query="SELECT * FROM ${oldtable} LIMIT 0"
    bq query --destination_table "${PROJECT_ID}:${newtable}" "$query"

    # create a table for Salt2 params
    oldtable="ztf_alerts.salt2"
    newtable="ztf_alerts_${testid}.salt2"
    query="SELECT * FROM ${oldtable} LIMIT 0"
    bq query --destination_table "${PROJECT_ID}:${newtable}" "$query"

fi
