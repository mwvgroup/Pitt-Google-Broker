# Pitt LSST Broker

This project explores the construction of an LSST broker. I'll be updating code and notes here for the duration of the DESC broker workshop and DESC collaboration meeting.

- [Action Items](#action-items)
- [Installation Instructions](#installation-instructions)
- [ZTF Data Access](#ztf-data-access)
- [Running a Kafka Stream](#running-a-kafka-stream)
- [Links and Resources](#links-and-resources)
    + [General](#general)
    + [LSST documents](#lsst-documents)
    + [ZTF](#ztf)



## Action Items

- [ ] Formalize design intentions - what would a Pitt LSST broker look like?
- [x] Download ZTF alert data for use in development and testing
- [x] Setup a rudimentary Kafka server for testing
- [ ] Wrap dependencies in a docker



## Installation Instructions

Although this project is python based, Apache Kafka is written in Scala. This means we will have to install both Python and Java packages. Note that this project relies on Python 3.7. It is recommended to install python dependencies in a dedicated environment:

```bash
> conda create -n pitt_broker python=3.7 anaconda
> conda activate pitt_broker
> pip install -r requirements.txt
```

Detailed Java installation instructions can be found [here](https://www.java.com/en/download/help/download_options.xml#mac)

Apache Kafka and Zookeeper download instructions can be found [here](https://www.tutorialspoint.com/apache_kafka/apache_kafka_installation_steps.htm)



## ZTF Data Access

This project will eventually connect to the ZTF. However, the live ZTF stream is still in beta and isn't publically available. In the meantime, we work with data from the [ZTF public alerts archive](https://ztf.uw.edu/alerts/public/). This has the same data but is released daily instead of as an alerts stream. Access is provided via the `data_access` package provided in this repo:

```python
# Download data from ZTF. By default only download 1 day
# Note: Daily releases can be as large as several G
from mock_stream import download_data
download_data()

# Retrieve the number of daily releases that have been downloaded
from mock_stream import number_local_releases
print(number_local_releases())

# Retrieve the number of alerts that have been downloaded
# from all combined daily releases.
from mock_stream import get_number_local_alerts
print(get_number_local_alerts())

# Iterate through local alert data
from mock_stream import iter_alerts
for alert in iter_alerts():
    alert_id = alert['candid']
    print(alert_id)
    break

# Get alert data for a specific id
from mock_stream import get_alert_data
alert_data = get_alert_data(alert_id)
print(alert_data)

# Plot stamp images for alert data
from matplotlib import pyplot as plt
from mock_stream import plot_stamps
fig = plot_stamps(alert_data)
plt.show()

```



## Running a Kafka Stream

The `run_kafka.sh` script is provided to run a demo Kafka server. The resulting server is the same as that created in the Kafka Quick Start guide. The script will prompt you for the directory where Kafka is installed.

```bash
> bash run_kafka.sh
Enter kafka directory: <./kafka_directory>

```

The resulting Kafka stream has one topic called `Demo-Topic`. To subscribe a consumer to this topic and populate kafka with a series of alerts:

```python
# Populate alert stream with up to 100 alerts.
# Use max_alerts argument for more or less alerts.
from mock_stream import prime_alerts
prime_alerts()

# At this point you can use the built in consumer object
from mock_stream import consumer

# You can also create your own consumer and point it to the
# beginning of the stream
from kafka import KafkaConsumer
consumer = KafkaConsumer('Demo-Topic',
                         bootstrap_servers=['localhost:9092'], 
                         auto_offset_reset='earliest')

# Iterate through alerts:
for alert in consumer:
    print(alert)

```

## Links and Resources

#### General

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
