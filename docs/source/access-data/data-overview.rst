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

Current streams include:

ztf-loop

    Use this stream for testing. Recent ZTF alerts are published to this topic
    at a constant rate of 1 per second, day and night.

ztf_alerts

    Full ZTF alert stream.

ztf_alerts_pure

    ZTF alert stream filtered for purity.

ztf_exgalac_trans

    ZTF alert stream filtered for likely extragalactic transients.

ztf_salt2

    Salt2 fits + alert contents of ZTF alerts that passed quality cuts and the
    likely-extragalactic-transients filter.

ztf_alert_avros

    Notification stream from the ztf-alert_avros Cloud Storage bucket indicating
    that a new alert packet is in file storage.
