# Pitt LSST Broker

Data from LSST will be distributed through three distinct avenues. The first is a real-time stream of alerts that provides information on transient targets within 60 seconds of observation. The second is a daily data release, which contains the same information as the 60-second alerts plus some additional information. The last data product will be a yearly data release.

The 60-second alert stream will not be made available to the public (at least not in its entirety). Instead, LSST will rely on a small number of (~7) community developed *broker* systems to publically relay the information. This project explores the construction of an LSST broker using the alert stream from the Zwicky Transient Factory (ZTF) as a testing ground.



- [Action Items](#action-items)
- [Installation Instructions](#installation-instructions)
- [ZTF Data Access](#ztf-data-access)
- [Running a Kafka Stream](#running-a-kafka-stream)
- [Links and Resources](#links-and-resources)
    + [General](#general)
    + [LSST documents](#lsst-documents)
    + [ZTF](#ztf)



## Action Items

- [x] Download ZTF alert data for use in development and testing
- [x] Setup a rudimentary Kafka server for testing
- [x] Wrap dependencies in a docker
- [ ] Formalize design intentions - what would a Pitt LSST broker look like?



## Installation Instructions

All Python dependencies are installable using `pip` and the `requirements.txt` file. To create a new conda environment and install dependencies, run:

```bash
> conda create -n pitt_broker python=3.7 anaconda
> conda activate pitt_broker  # Activate the new environment
> pip install -r requirements.txt
> conda deactivate  # Exit the environment
```

This project also relies on dependencies that are not written in Python. These have been Dockerized for convenience and don't require any dedicated installation. However, you will need to download [Docker](https://docs.docker.com/install/) (Click the link and scroll down to the *Supported platforms* section).



## ZTF Data Access

This project will use ZTF data for testing and development. Although the live ZTF alert stream is still in beta and isn't publically available, all alerts are submitted at the end of the day to the [ZTF public alerts archive](https://ztf.uw.edu/alerts/public/). This repository provides the `mock_stream` module which is capable of automatically downloading, parsing, and plotting results from the public archive. The following example demonstrates each of these capabilities: 

```python
from matplotlib import pyplot as plt

from mock_stream import download_data
from mock_stream import get_alert_data
from mock_stream import get_number_local_alerts
from mock_stream import iter_alerts
from mock_stream import number_local_releases
from mock_stream import plot_stamps

# Download data from ZTF. By default only download 1 day
# Note: Daily releases can be as large as several G
download_data()

# Retrieve the number of daily releases that have been downloaded
print(number_local_releases())

# Retrieve the number of alerts that have been downloaded
# from all combined daily releases.
print(get_number_local_alerts())

# Iterate through local alert data
for alert in iter_alerts():
    alert_id = alert['candid']
    print(alert_id)
    break

# Get alert data for a specific id
alert_data = get_alert_data(alert_id)
print(alert_data)

# Plot stamp images for alert data
fig = plot_stamps(alert_data)
plt.show()

```



## Running a Kafka Stream

The `mock_stream` module also provides a simulated stream of ZTF alerts. Just like the real ZTF stream, alerts are streamed using a [Kafka server](https://kafka.apache.org/intro). LSST will eventually use the same type of server system. To initialize a local server for testing, run:

```bash
> docker-compose up 
```

If you are having problems with Kafka server, try adding the `--force-recreate` argument to avoid using a cached server image. You can also check the status of any docker images running on your machine by executing `docker stats` in a separate window. Note that the above command actually initializes two docker containers - one for Kafka, and one for Zookeeper which manages the Kafka server.



The resulting Kafka stream has a single topic called `ztf-stream`. To subscribe a consumer to this topic and populate Kafka with a series of alerts:

```python
from kafka import KafkaConsumer
from mock_stream import prime_alerts

# Create a consumer
consumer = KafkaConsumer(
    'ztf-stream',
    bootstrap_servers=['localhost:9092']
)

# Populate alert stream with up to 100 alerts.
# Use max_alerts argument for more or fewer alerts.
prime_alerts()

# Iterate through alerts
# Note that it takes a moment for Kafka to process alerts
# and the consumer may not have access to them right away
for alert in consumer:
    print(alert)

```



## Links and Resources

#### General

- Project notes: [here](./notes/)
- Online LSST forum for data managment (DM): [community.lsst.org/](https://community.lsst.org/)
- LSST-DESC Broker Workshop talks [drive.google.com/...](https://drive.google.com/drive/folders/1sjYXbdwTID3VnzZNAkcjLbjRfpwNaO_n?usp=sharing) 



#### LSST Documents

- Plans and Policies for alert distribution (how will community brokers be chosen?): [ls.st/LDM-612](https://ls.st/LDM-612)
- Call for letters ofiIntent for community alert brokers (how do I apply to be a community broker?): [ls.st/LDM-682](https://ls.st/LDM-682)
- LSST alerts: key numbers (how many? how much? how often?): [dmtn-102.lsst.io](https://dmtn-102.lsst.io)
- Data Products Definition Document (DPDD) (What data will LSST deliver?): [ls.st/dpdd](https://ls.st/dpdd)
- Prototype schemas: [github.com/lsst-dm/sample-avro-alert](https://github.com/lsst-dm/sample-avro-alert)
- Kafka-based alert stream: [github.com/lsst-dm/alert_stream](https://github.com/lsst-dm/alert_stream)



#### ZTF

- Sample alert packets: [ztf.uw.edu/alerts/public/](https://ztf.uw.edu/alerts/public/)
- Alert packet tools: [zwicky.tf/4t5](https://zwicky.tf/4t5)
- Alert schema documentation: [zwicky.tf/dm5](https://zwicky.tf/dm5)
- Detailed pipelines documentation: [zwicky.tf/ykv](https://zwicky.tf/ykv)
- PASP instrument papers: [zwicky.tf/3w9](https://zwicky.tf/3w9)
