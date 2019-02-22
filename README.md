# Pitt LSST Broker

This project explores the construction of an LSST broker.

- [Action Items](#action-items)
- [ZTF Data Access](#ztf-data-access)
- [Links and Resources](#links-and-resources)
  - [General](#general)
  - [LSST documents](#lsst-documents)
  - [ZTF](#ztf)



## Action Items

- [ ] Formalize design intentions - what would a Pitt LSST broker look like?
- [ ] Download ZTF alert data for use in development and testing
- [ ] Setup a rudimentary Kafka server for testing



## ZTF Data Access

This project will eventually connect to the ZTF. However, the live ZTF stream is still in beta and isn't publically available. In the meantime, we work with data from the [ZTF public alerts archive](https://ztf.uw.edu/alerts/public/). This has the same data but is released daily instead of as an alerts stream. Access is provided via the `data_access` package provided in this repo:

```python
# Download data from ZTF. By default only download 1 day
# Note: Daily releases can be as large as several G
from data_access import download_data
download_data()

# Retrieve the number of daily releases that have been downloaded
from data_access import number_local_releases
print(number_local_releases())

# Retrieve the number of alerts that have been downloaded
# from all combined daily releases.
from data_access import get_number_local_alerts
print(get_number_local_alerts())

# Iterate through local alert data
from data_access import iter_alerts
for alert in iter_alerts():
    alert_id = alert['candid']
    print(alert_id)
    break

# Get alert data for a specific id
from data_access import get_alert_data
alert_data = get_alert_data(alert_id)
print(alert_data)

# Plot stamp images for alert data
from matplotlib import pyplot as plt
from data_access import plot_stamps
fig = plot_stamps(alert_data)
plt.show()

```



## Links and Resources

#### General:

- Online LSST forum for data managment (DM): [community.lsst.org/](https://community.lsst.org/)
- LSST-DESC Broker Workshop talks [drive.google.com/...](https://drive.google.com/drive/folders/1sjYXbdwTID3VnzZNAkcjLbjRfpwNaO_n?usp=sharing) 



#### LSST documents:

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