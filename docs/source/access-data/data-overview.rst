Data Overview
=============

Pub/Sub
----------------

Pub/Sub is an asynchronous, publish–subscribe messaging service.
The Pitt-Google broker publishes alerts and value-added data to multiple topics,
listed below.
You can subscribe to one or more of these topics,
and then pull and process the message stream(s).
See the :doc:`tutorials/pubsub` tutorial for more information.

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

    * - ztf-alert_avros
      - Notification stream from the ztf-alert_avros Cloud Storage bucket indicating
        that a new alert packet is in file storage.
        These messages contain no data, only attributes.
        The file name is in the attribute "objectId",
        and the bucket name is in the attribute "bucketId".


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
