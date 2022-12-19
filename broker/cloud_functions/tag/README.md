# tag

Identify basic categorizations.
Publish results to BigQuery and as Pub/Sub msg attributes.


## is_pure

Adapted from: https://zwickytransientfacility.github.io/ztf-avro-alert/filtering.html

Quoted from the source:

ZTF alert streams contain an nearly entirely unfiltered stream of all
5-sigma (only the most obvious artefacts are rejected). Depending on your
science case, you may wish to improve the purity of your sample by filtering
the data on the included attributes.
Based on tests done at IPAC (F. Masci, priv. comm), the following filter
delivers a relatively pure sample.

## is_extragalactic_transient

Check whether alert is likely to be an extragalactic transient.
Adapted from: https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
