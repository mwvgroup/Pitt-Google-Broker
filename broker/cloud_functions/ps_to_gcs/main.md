# Pub/Sub -> GCS Cloud Function for alert Avro files

__Deploy__
```python
cd deploy2cloud_Aug2020/ps-to-gcs/
# topic=troy_test_topic
topic=ztf_alert_data
gcloud functions deploy upload_ztf_bytes_to_bucket \
    --runtime python37 \
    --trigger-topic ${topic}

```

__Get an alert and figure out how to parse the data/attributes:__
```python
from google.cloud import pubsub_v1
import main as mn

project_id = 'ardent-cycling-243415'
subscription_id = 'troy_test_topic'
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)
response = subscriber.pull(subscription_path, max_messages=1)
for received_message in response.received_messages:
    msg = received_message.message

# data = base64.b64decode(msg.data)  # alert packet, bytes
data = msg.data  # alert packet, bytes
atrs = msg.attributes  # dict of custom attributes
```

__test the fnc; fix schema and upload__
```python
filename = f"{atrs['kafka.topic']}_{atrs['kafka.timestamp']}_trial.avro"
# bucket_name = 'ardent-cycling-243415_ztf_alert_avro_bucket'
bucket_name = 'ardent-cycling-243415_testing_bucket'

logging_client = logging.Client()
log_name = 'ps-to-gcs-cloudfnc'
logger = logging_client.logger(log_name)

storage_client = storage.Client()
bucket = storage_client.get_bucket(bucket_name)
# logger.log_text(f'Uploading {filename} to {bucket.name}')
blob = bucket.blob(filename)
#

survey = mn.guess_schema_survey(data)
version = mn.guess_schema_version(data)

max_alert_packet_size = 150000
with mn.TempAlertFile(max_size=max_alert_packet_size, mode='w+b') as temp_file:
    temp_file.write(data)
    temp_file.seek(0)
    mn.fix_schema(temp_file, survey, version)
    dfix = temp_file.read()
    temp_file.seek(0)
    blob.upload_from_file(temp_file)
# the above works
```

Logging: [Using the Logging Client Libraries](https://cloud.google.com/logging/docs/reference/libraries)


__Deploy the Cloud Function__
```bash
cd deploy2cloud_Aug2020/ps-to-gcs/
# topic=troy_test_topic
gcloud functions deploy upload_bytes_to_bucket \
    --runtime python37 \
    --trigger-topic ${topic}
```

__Trigger the cloud function by publishing the msg we pulled earlier__
```python
publisher = pubsub_v1.PublisherClient()
topic_name = 'troy_test_topic'
topic_path = publisher.topic_path(project_id, topic_name)
attrs = {'kafka.topic': msg.attributes['kafka.topic'],
         'kafka.timestamp': msg.attributes['kafka.timestamp']}
future = publisher.publish(topic_path, data=msg.data, **attrs)
```

__download file from GCS and see if i can open/read it__
```python
# download the file
gcs_fname = f"{atrs['kafka.topic']}_{atrs['kafka.timestamp']}_trial.avro"
bucket_name = 'ardent-cycling-243415_ztf_alert_avro_bucket'
bucket = storage_client.get_bucket(bucket_name)
blob = bucket.blob(gcs_fname)
blob.download_to_filename(gcs_fname)
blob.delete()
# open it
# import fastavro
# fworks = '/Users/troyraen/Documents/PGB/repo/tests/test_alerts/ztf_3.3_validschema_1154446891615015011.avro'
from broker.alert_ingestion.gen_valid_schema import _load_Avro
schema, data = _load_Avro(gcs_fname)
# this works
```

__Setup PubSub notifications on GCS bucket__
- [Using Pub/Sub notifications for Cloud Storage](https://cloud.google.com/storage/docs/reporting-changes#gsutil)

```bash
BUCKET_NAME='ardent-cycling-243415_ztf_alert_avro_bucket'
TOPIC_NAME='projects/ardent-cycling-243415/topics/ztf_alert_avro_bucket'
format=json  # json or none; whether to deliver the payload with the PS msg
# create the notifications -> PS
gsutil notification create \
            -t ${TOPIC_NAME} \
            -e OBJECT_FINALIZE \
            -f ${format} \
            gs://${BUCKET_NAME}

# check the notifications on the bucket
gsutil notification list gs://${BUCKET_NAME}

# remove the notification
CONFIGURATION_NAME=11  # get from list command above
gsutil notification delete projects/_/buckets/${BUCKET_NAME}/notificationConfigs/${CONFIGURATION_NAME}
```

__count the number of objects in the bucket matching day's topic__
```bash
gsutil ls gs://ardent-cycling-243415_ztf_alert_avro_bucket/ztf_20201227_programid1_*.avro > dec27.count
wc -l dec27.count
```
