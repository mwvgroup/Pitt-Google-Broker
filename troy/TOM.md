# Connecting to TOM Toolkit, DESC Elasticc

- [TOM Toolkit](https://tom-toolkit.readthedocs.io/en/stable/index.html)

- [tom_desc](https://github.com/LSSTDESC/tom_desc)
    - [ingestmessages.py](https://github.com/LSSTDESC/tom_desc/blob/main/stream/management/commands/ingestmessages.py) (ingest SCIMMA)

- [tom_fink](https://github.com/TOMToolkit/tom_fink/blob/main/tom_fink/fink.py)

ToDo:

- run Django
- run TOM
- run `tom_desc`
- run `tom_fink`
- change `ingestmessages.py` to listen to our stream
- add us as a `tom_toolkit` module

---

- Following [TOM Toolkit Getting Started](https://tom-toolkit.readthedocs.io/en/stable/introduction/getting_started.html)

```bash
conda create --name tom python=3.7
conda activate tom

# use mypgb test account
# export GOOGLE_CLOUD_PROJECT=my-pgb-project-3
# export GOOGLE_APPLICATION_CREDENTIALS=/Users/troyraen/Documents/broker/repo/GCP_auth_key-mypgb-raentroy.json
# export PITTGOOGLE_OAUTH_CLIENT_ID="187635371164-eoeg3i6vp4bcd26p7l8cvjir3ga6nb7a.apps.googleusercontent.com"

export PITTGOOGLE_OAUTH_CLIENT_ID="591409139500-hb4506vjuao7nvq40k509n7lljf3o3oo.apps.googleusercontent.com"
export PITTGOOGLE_OAUTH_CLIENT_SECRET=""
# /Users/troyraen/Documents/broker/repo/GCP_oauth-client_secret.json

# add tom_pittgoogle to path
python -m pip install -e .
# export PYTHONPATH="${PYTHONPATH}:/Users/troyraen/Documents/broker/tom/tom_pittgoogle"
# export DJANGO_SETTINGS_MODULE=tom_pittgoogle.settings

# export PYTHONPATH="${PYTHONPATH}:/Users/troyraen/Documents/broker/tommy/tommy"
export DJANGO_SETTINGS_MODULE=tommy.settings

# pip install requests requests_oauthlib
pip install google-cloud-bigquery
pip install google-cloud-pubsub
pip install fastavro
pip install requests_oauthlib

pip install tomtoolkit
# create a new project
django-admin startproject tommy

cd tommy

# edit settings to add tom_setup. then:
./manage.py tom_setup
./manage.py migrate
./manage.py runserver
# navigate to http://127.0.0.1:8000/

# to make updates
./manage.py makemigrations
./manage.py migrate
./manage.py runserver
```

Register an app

```python
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tommy.settings')
application = get_wsgi_application()
```

Add some things from our [Broker-Web](https://github.com/mwvgroup/Broker-Web)

Print more helpful errors for
`RuntimeError("populate() isn't reentrant")`
- edit `django/apps/registry.py` as described [here](https://stackoverflow.com/questions/27093746/django-stops-working-with-runtimeerror-populate-isnt-reentrant)

## Build in RTD

```bash
export BUILD_IN_RTD=True
export DJANGO_SETTINGS_MODULE=tom_pittgoogle.settings
export SECRET_KEY='4iq)g7qh+1+0g03$!3kx0@*=v!#2ioi@^-f=-^ix6l(z7c_6d8'
```

Put at top of python modules, if needed:
```python
import os
import troy_fncs as tfncs
settings = tfncs.AttributeDict({
    'GOOGLE_CLOUD_PROJECT': os.getenv('GOOGLE_CLOUD_PROJECT'),
    'PITTGOOGLE_OAUTH_CLIENT_ID': '591409139500-hb4506vjuao7nvq40k509n7lljf3o3oo.apps.googleusercontent.com',
    'PITTGOOGLE_OAUTH_CLIENT_SECRET': "<FILL-IN>",
})
```

## Run StreamPython locally

```python
clean_params = {
    'subscription_name': 'ztf-loop',
    'classtar_threshold': None,
    'classtar_gt_lt': 'gt',
    'max_results': 100,

}
```

## Message size

```python
from python_fncs.pubsub_consumer import Consumer as Consumer

consumer = Consumer('ztf-loop')
msgs = consumer.stream_alerts(parameters={'max_results': 1, 'max_backlog': 1})
msg = msgs[0]
msg.size  # bytes
# result is: 67362

# 1 TiB ~= 1.6e7 alerts = $40
```
