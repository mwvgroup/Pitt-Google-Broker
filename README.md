# Pitt LSST Broker

This project explores the construction of an LSST broker.


## Action Items

- [ ] Formalize design intentions - what would an Pitt - LSST broker look like?
- [ ] Download ZTF alert data for use in development and testing
- [ ] Setup a rudementary Kafka server


## Table of Contents

- [Links and Resources](#links-and-resources)
    + [General:](#general-)
    + [LSST documents:](#lsst-documents-)
    + [ZTF](#ztf)


## Links and Resources

#### General:

- Online LSST forum for DM: [community.lsst.org/](https://community.lsst.org/)
- LSST-DESC Broker Workshop talks [drive.google.com/...](https://drive.google.com/drive/folders/1sjYXbdwTID3VnzZNAkcjLbjRfpwNaO_n?usp=sharing) 

#### LSST documents:

- Plans and Policies for Alert Distribution (how will community brokers be chosen?): [ls.st/LDM-612](https://ls.st/LDM-612)
- Data Products Definition Document LSE-163 (what will LSST alerts look like?): [ls.st/dpdd](https://ls.st/dpdd)
- Call for Letters of Intent for Community Alert Brokers (how do I apply to be a community broker?): [ls.st/LDM-682](https://ls.st/LDM-682)
- LSST Alerts: Key Numbers (how many? how much? how often?): [dmtn-102.lsst.io](https://dmtn-102.lsst.io)
- Data Products Definition Document (What data will LSST deliver?): [ls.st/dpdd](https://ls.st/dpdd)
- Prototype Schemas: [github.com/lsst-dm/sample-avro-alert](https://github.com/lsst-dm/sample-avro-alert)
- Kafka-based Alert Stream: [github.com/lsst-dm/alert_stream](https://github.com/lsst-dm/alert_stream)

#### ZTF

- Sample Alert Packets: [ztf.uw.edu/alerts/public/](https://ztf.uw.edu/alerts/public/)
- Alert Packet Tools: [zwicky.tf/4t5](https://zwicky.tf/4t5)
- Alert Schema Documentation: [zwicky.tf/dm5](https://zwicky.tf/dm5)
- Detailed Pipelines documentation: [zwicky.tf/ykv](https://zwicky.tf/ykv)
- PASP instrument papers: [zwicky.tf/3w9](https://zwicky.tf/3w9)