# `pgb_broker_utils`

- `pip install pgb_broker_utils`
- `import broker_utils`

Note that the schema maps are stored in a Cloud Storage bucket and are not packaged with this module.
This has the following benefits:
1. Schema maps can be updated easily by uploading new files to the bucket.
2. Broker instances can use different schema maps; each instance loads them from their own `broker_files` bucket.
