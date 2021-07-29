# Cloud File Storage

- [Prerequisites](#prerequisites)
- [File names](#file-names)
- [Python](#python)
- [gsutil command-line tool](#gsutil-command-line-tool)

This tutorial covers downloading and working with files from our Cloud Storage buckets via two methods: the pgb-utils Python package, and the gsutil CLI.

For more information, see:
- [Google Cloud Storage Client Python documentation](https://googleapis.dev/python/storage/latest/client.html)
- [gsutil overview](https://cloud.google.com/storage/docs/gsutil)

## Prerequisites

1. Complete the [Initial Setup](initial-setup.md). Be sure to:
    - set your environment variables
    - enable the Cloud Storage API
    - install the google-cloud-bigquery package if you want to use Python
    - install the pgb-utils package if you want to plot the data using Python
    - install the CLI if you want to use the command line

## Files names

We store the alert packets as Avro files named as "{objectId}.{candid}.{ztf_topic}.avro"

## Python

### Setup
Imports
```python
from google.cloud import storage
import pgb_utils as pgb
```

Name some things
```python
# fill in the path to the local directory to which you want to download files
local_dir = ''

my_project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
pgb_project_id = 'ardent-cycling-243415'
```

### Download files

Download alerts for a given `objectId`
```python
objectId = 'ZTF17aaackje'
bucket_name = f'{pgb_project_id}-ztf-alert_avros'

# Create a client and request a list of files
storage_client = storage.Client(my_project_id)
bucket = storage_client.get_bucket(bucket_name)
blobs = bucket.list_blobs(prefix=objectId)

# download the files
for blob in blobs:
    local_path = f'{local_dir}/{blob.name}'
    blob.download_to_filename(local_path)
    print(f'Downloaded {local_path}')
```

### Plot cutouts and lightcurves

The functions in this section were adapted from https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb.

Open a file
(see the previous section to download files)

```python
paths = Path(local_dir).glob('*.avro')
for path in paths:
    with open(path, 'rb') as fin:
        alert_list = [r for r in fastavro.reader(fin)]
    break
alert_dict = alert_list[0]  # extract the single alert packet

print(alert_dict.keys())
```

Plot cutouts

```python
pgb.figures.plot_cutouts(alert_dict)
```

Cast to a dataframe and plot lightcurves

```python
lc_df = pgb.utils.alert_dict_to_dataframe(alert_dict)
pgb.figures.plot_lightcurve(lc_df)
```

Plot everything together

```python
pgb.figures.plot_lightcurve_cutouts(alert_dict)
```

## gsutil command-line tool

See also:
- [Quickstart: Using the gsutil tool](https://cloud.google.com/storage/docs/quickstart-gsutil)
- [`gsutil cp` - Copy files and objects](https://cloud.google.com/storage/docs/gsutil/commands/cp)

Get help
```bash
gsutil help
gsutil help cp
```

Download a single file
```bash
# fill in the path to the local directory to which you want to download files
local_dir=
# fill in the name of the file you want. see above for the syntax
file_name=
# file_name=ZTF17aaackje.1563161493315010012.ztf_20210413_programid1.avro
avro_bucket="${pgb_project_id}-ztf-alert_avros"

gsutil cp "gs://${avro_bucket}/${file_name}" ${local_dir}/.
```
