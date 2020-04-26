What is Pitt Broker
===================

The **Pitt-Google Broker** is a cloud-based, alert distribution service
designed to provide near real-time processing of data from
large-scale astronomical surveys like the `Legacy Survey of Space and Time
<https://www.lsst.org>`_ (LSST). LSST will deliver on order a million real-time
alerts each night providing information on astronomical targets within 60
seconds of observation. The **Pitt-Google Broker** is a scalable broker
system designed to maximize the availability and usefulness of the LSST alert
data by combining cloud-based analysis opportunities with value-added data
products.

The **Pitt-Google Broker** is designed to run on the `Google Cloud Platform
<https://cloud.google.com>`_ (GCP) and is currently focused on processing
alerts from the `Zwicky Transient Facility <https://www.ztf.caltech.edu>`_
(ZTF) and the `LSST Alert Simulator
<https://www.lsst.org/scientists/simulations/alertsim>`_ (AlertSim) as a
testing ground.

.. toctree::
   :hidden:
   :maxdepth: 1

   Overview<self>

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Installation and Setup:

   installation_setup/installation
   installation_setup/developer_dependencies
   installation_setup/configuring_travis
   installation_setup/deploying_images
   installation_setup/scheduling_ingestion

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Quick Start Guides:

   quick_start/ztf_archive
   quick_start/xmatch

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Module Documentation:

   module_docs/alert_ingestion
   module_docs/value_added
   module_docs/pub_sub_client
   module_docs/ztf_archive
