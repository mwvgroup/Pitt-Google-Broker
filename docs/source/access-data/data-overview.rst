Data Overview
=============

We are currently processing the ZTF alert stream.
Data is available in message streams (Pub/Sub),
database tables (BigQuery), and
Avro files (Cloud Storage).
The data lives in the Google Cloud and can be accessed via their many APIs.
Our tutorials demonstrate Python and the command line,
and give links to further information.

Pub/Sub
----------------

Pub/Sub is an asynchronous, publish–subscribe messaging service.
The Pitt-Google broker publishes alerts and value-added data to multiple topics,
listed below.
You can subscribe to one or more of these topics,
and then pull and process the message stream(s)
(see the :doc:`pubsub` tutorial).

.. list-table:: Current Streams
    :class: tight-table
    :widths: 25 75
    :header-rows: 1

    * - Topic
      - Description

    * - ztf-loop
      - Use this stream for testing. Recent ZTF alerts are published to this topic
        at a constant rate of 1 per second, day and night.

    * - ztf-alerts
      - Full ZTF alert stream.

    * - ztf-alerts_pure
      - ZTF alert stream filtered for purity.

    * - ztf-exgalac_trans
      - ZTF alert stream filtered for likely extragalactic transients.

    * - ztf-salt2
      - Salt2 fits + alert contents of ZTF alerts that passed quality cuts and the
        likely-extragalactic-transients filter.

    * - ztf-SuperNNova
      - SuperNNova classification results (Ia vs non-Ia) + alert contents of ZTF
        alerts that passed the likely-extragalactic-transients filter.

    * - ztf-alert_avros
      - Notification stream from the ztf-alert_avros Cloud Storage bucket indicating
        that a new alert packet is in file storage.
        These messages contain no data, only attributes.
        The file name is in the attribute "objectId",
        and the bucket name is in the attribute "bucketId".

BigQuery
----------------

BigQuery is a data warehouse service designed for scalable analysis over
petabytes of data.

We store the alert content (except cutouts) and our value-added products in
BigQuery tables, available for public queries.
See the :doc:`bigquery` tutorial.


Cloud Storage
----------------

Google Cloud Storage is a RESTful file storage web service.
We store the complete alert packets, including cutouts,
as well as value-added products from our pipeline as applicable
in publicly accesible Cloud Storage buckets.
See the :doc:`cloud-storage` tutorial.


Note on Costs
---------------

You do not need to setup billing to complete our tutorials.
The Google Cloud services pricing structure includes a Free Tier,
and the usage incurred from our tutorials stays well within these limits.

You cannot be charged unless you explicitly enable billing for your project
and setup a billing account.

For users who wish to process volumes of data larger than the Free Tier quotas,
Google's pricing structure is "pay-as-you-go"
and you only pay for what you actually use.
See the links below for more information.

Some pricing examples (as of Aug. 2021):

.. list-table::
    :class: tight-table
    :widths: 15 20 20 20
    :header-rows: 1

    * - Service
      - Activity
      - Free Tier quota
      - Price beyond Free Tier
    * - BigQuery
      - querying data
      - 1 TB per month
      - $5.00 per TB
    * - Pub/Sub
      - message delivery
      - 10 GB per month
      - $40 per TB

For more information, see:

- `Free Tier <https://cloud.google.com/free>`__
- `Pricing structure <https://cloud.google.com/pricing>`__
  (scroll to "Only pay for what you use")
- `Detailed price list <https://cloud.google.com/pricing/list>`__
  (search for "BigQuery", "Cloud Storage", "Pub/Sub");
- `Pricing calculator <https://cloud.google.com/products/calculator?skip_cache=true>`__
  (same search as above)
- `Create a billing account
  <https://cloud.google.com/billing/docs/how-to/manage-billing-account>`__
- `Enable billing for a project
  <https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project>`__
