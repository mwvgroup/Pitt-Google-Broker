
# BigQuery schema json
We need a:
- list of dictionaries, each with keys:
    - description - string
    - mode - one of [REQUIRED, REPEATED, NULLABLE]
    - name - string, no spaces
    - type - one of [INTEGER, FLOAT, STRING, RECORD]
    - fields (if type == RECORD) - list of dictionaries with the same keys as listed above

Download the decat schemas
```bash
git clone https://github.com/rknop/decat_schema.git
```

Create the json for BigQuery
```python
from fastavro.schema import load_schema
import json

# look at the ztf BQ schema to understand what's needed
fztfschema = '../broker/setup_broker/templates/bq_ztf_alerts_schema.json'
with open(fztfschema) as f:
    ztfschema = json.load(f)

# load decat object and source schemas
dobject = load_schema('decat_schema/decat_object.avsc')['fields']
dsource = load_schema('decat_schema/decat_source.avsc')['fields']

#--- Create a single list of dicts to dump to json
def get_mode(oitem):
    otype = oitem['type']
    if type(otype)==list and otype[0]=='null':
        mode = 'NULLABLE'
    elif type(otype)==dict and otype['type'] == 'array':
        mode = 'REPEATED'
    else:
        mode = 'REQUIRED'
    return mode

def get_type(oitem):
    otype = oitem['type']
    if type(otype) == str:
        typ = otype.upper()
    elif type(otype) == list:
        typ = otype[-1].upper()
    elif type(otype)==dict and otype['type'] == 'array':
        if otype['items'] == 'decat.source':
            typ = 'RECORD'
        else:
            typ = otype['items'].upper()
    if typ == 'INT': typ = 'INTEGER'
    if typ == 'DECAT.SOURCE': typ = 'RECORD'
    return typ

def get_diasource_fields(column):
    if column['name'] != 'triggersource':
        return column
    else:
        # rename columns with same names as an object-level attribute
        dup_cols = ['ra','dec']
        lam = lambda x: x if x not in dup_cols else f'source_{x}'
        c = {lam(key): val for key, val in column.items()}
        return c

# create a record for a source
dsource_bq = []
for item in dsource:
    column = {
        'description': item['doc'],
        'mode': get_mode(item),
        'name': item['name'],
        'type': get_type(item),
    }
    if item['name'] not in ['scicutout', 'refcutout', 'diffcutout']:
        dsource_bq.append(column)

# create a record for an alert and a source
alerts_schema_bq = []
DIASource_schema_bq = []
for oitem in dobject:
    column = {
        'description': oitem['doc'],
        'mode': get_mode(oitem),
        'name': oitem['name'],
        'type': get_type(oitem),
    }
    if column['type'] == 'RECORD':
        column['fields'] = dsource_bq

    alerts_schema_bq.append(column)

    if column['name'] != 'sources':
        DIASource_schema_bq.append(get_diasource_fields(column))


# write the files
falerts = '../broker/setup_broker/templates/bq_decat_alerts_schema.json'
fsource = '../broker/setup_broker/templates/bq_decat_DIASource_schema.json'
z = zip([falerts, fsource], [alerts_schema_bq, DIASource_schema_bq])
for ff, schema in z:
    with open(ff, 'w') as f:
        json.dump(dschema_bq, f, indent=2)
```

Make the tables (test what `setup_gcp.py` will do)
```
projectid=ardent-cycling-243415
dataset=ztf_alerts_decam

bq mk --table "${projectid}:${dataset}.alerts" templates/bq_decat_alerts_schema.json
bq mk --table "${projectid}:${dataset}.DIASource" templates/bq_decat_DIASource_schema.json
bq mk --table "${projectid}:${dataset}.salt2" templates/bq_decat_salt2_schema.json

bq rm --table "${projectid}:${dataset}.alerts"
bq rm --table "${projectid}:${dataset}.DIASource"
bq rm --table "${projectid}:${dataset}.salt2"
```
