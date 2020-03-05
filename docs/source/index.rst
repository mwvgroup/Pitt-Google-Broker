.. Convert md to rst: https://pandoc.org/try/

What is Pitt Broker
===================

**Pitt Broker** is a cloud-based, alert distribution service designed to provide
near real-time processing for alerts from the `Large Synoptic Survey Telescope
<https://www.lsst.org>`_ (LSST). One of the primary data products LSST will
deliver is a real-time stream of alerts that provides information on transient
targets within 60 seconds of observation. Instead of providing this alert
stream  directly to the public, LSST will rely on community-developed *broker*
systems to relay the information. **Pitt Broker** is designed to maximize the
scalable availability and usefulness of the LSST alert data by combining
cloud-based analysis opportunities with value-added data products.

**Pitt Broker** is designed to run on the `Google Cloud Platform
<https://cloud.google.com>`_ (GCP) and is currently focused on processing
alerts from the `Zwicky Transient Facility <https://www.ztf.caltech.edu>`_
(ZTF) and the `LSST Alert Simulator
<https://www.lsst.org/scientists/simulations/alertsim>`_ (AlertSim) as a
testing ground.

Additional Resources
====================

For questions concerning the technical specifications of LSST or ZTF, the
following may prove to be useful.

LSST References
---------------

-  Plans and Policies for alert distribution: `ls.st/LDM-612`_
-  Call for letters of intent for community alert brokers: `ls.st/LDM-682`_
-  LSST alerts: key numbers (how many? how much? how often?):
   `dmtn-102.lsst.io`_
-  Data Products Definition Document (DPDD) (What data will LSST
   deliver?): `ls.st/dpdd`_
-  Prototype schemas: `github.com/lsst-dm/sample-avro-alert`_
-  Kafka-based alert stream: `github.com/lsst-dm/alert_stream`_

ZTF References
--------------

-  Sample alert packets: `ztf.uw.edu/alerts/public/`_
-  Alert packet tools: `zwicky.tf/4t5`_
-  Alert schema documentation: `zwicky.tf/dm5`_
-  Detailed pipelines documentation: `zwicky.tf/ykv`_
-  PASP instrument papers: `zwicky.tf/3w9`_

.. _ls.st/LDM-612: https://ls.st/LDM-612
.. _ls.st/LDM-682: https://ls.st/LDM-682
.. _dmtn-102.lsst.io: https://dmtn-102.lsst.io
.. _ls.st/dpdd: https://ls.st/dpdd
.. _github.com/lsst-dm/sample-avro-alert: https://github.com/lsst-dm/sample-avro-alert
.. _github.com/lsst-dm/alert_stream: https://github.com/lsst-dm/alert_stream
.. _ztf.uw.edu/alerts/public/: https://ztf.uw.edu/alerts/public/
.. _zwicky.tf/4t5: https://zwicky.tf/4t5
.. _zwicky.tf/dm5: https://zwicky.tf/dm5
.. _zwicky.tf/ykv: https://zwicky.tf/ykv
.. _zwicky.tf/3w9: https://zwicky.tf/3w9

.. toctree::
   :hidden:
   :maxdepth: 1

   Overview<self>
   installation


.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Quick Start:

   quick_start/ztf_archive
   quick_start/alert_ingestion
   quick_start/xmatch

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Module Documentation:

   module_docs/broker
   module_docs/consumer
   module_docs/value_added
   module_docs/pub_sub_client
   module_docs/ztf_archive
