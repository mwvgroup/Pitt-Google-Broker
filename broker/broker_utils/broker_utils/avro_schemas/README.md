# ELAsTiCC Schemas

Note: To add a new schema, add the avsc file(s) to this directory,
then register the schema in load.py.

There are currently two registered schemas:

- elasticc.v0_9.alert.avsc (incoming alerts from elasticc)
- elasticc.v0_9.brokerClassification.avsc (outgoing alerts to elasticc)

The other files are used by the alert schema.

The files were downloaded from the LSSTDESC repo using the following code:

```bash
v="elasticc.v0_9"
format="avsc"
baseurl="https://raw.githubusercontent.com/LSSTDESC/elasticc/main/alert_schema/"
schemas=(alert diaSource diaForcedSource diaNondetectionLimit diaObject brokerClassification)

for schema in ${schemas[@]}; do
    fname="${v}.${schema}.${format}"
    curl -L -o "${fname}" "${baseurl}${fname}"
done
```
