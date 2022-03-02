# DESC Broker Workshop

This document provides notes on the LSST-DESC Broker Workshop.
[Link to Talks](https://drive.google.com/drive/folders/1sjYXbdwTID3VnzZNAkcjLbjRfpwNaO_n?usp=sharing)

## Thursday Session 1: Science Vision and Precursor Surveys

### Lessons learned from microlensing follow-up (Rachel Street)

- Microlensing requires rapid followup (Usually \< 10 alerts per day)
- You need redundancy in followup locations to deal with weather and down time
- Data should be shared in real time with clear publication guidelines
  - Clear policy from each team over use of their telescope time/data
  - Clear procedure if someone is interested in analyzing/publishing on a target/topic
  - Clearly identify who should be notified and when
  - Incentive “playing nice”, penalize those who don’t
- Don't just build systems in advance - train people to use them in advance
- Avoid gold rush syndrome. Balance detailed follow up with a small number of targets
  with broader followup of many targets

### Black Hole Microlensing with Parallax (Nathan Golovich @ LLNL)

- Discussed why this topic is scientifically interesting
- How will the alert system handel long time scale signals with weak signal to noise?
- How will the catalogue / broker handel objects that have large parallax?
- Understanding the optimal cadence for different objects is important for creating an
  observing strategy.

### Microlensing with ZTF: Breaking in Spin with Brokers (Michael Medford @ LBNL)

- **Z**TF **A**lert **P**acket **I**nspection **T**ool
- Capture
  - Ingest ZTF alert packet data through Kafka consumer
  - Cross-match detections into long duration light-curves
- Detect
  - Regularly filter for ongoing and completed microlensing events
  - Remove false positives, mainly variable stars
- Characterize
  - Fit microlensing events to model parameters
  - Calculate optical depths, Einstein crossing time distributions, and dark matter
    constraints
- Existing brokers have specific science cases in mind that don't always scale to the
  general community.
- NERSC is capable of processing the data from 47 deg2 every 30 seconds in realtime
  (~O(105) per night)
  - Host of complimentary services including HPSS tape archive, science gateways, NERSC
    web Toolkit (NEWT) HTML API, Spin, etc.
- ZAPIT v0.5 is currently running on NERSC’s Spin pilot phase
  - Containers-as-a-Service platform based on Docker container technology
  - All the convenient benefits of docker (DBs, web service, scalability) and all of the
    computational firepower of NERSC

### The ZTF Coadd Facility (Danny Goldstein @ Caltech)

- Combines images from multiple observations to create deeper stacks.
- Reduces functional cadence, but increases the number of discovered objects

## Thursday Session 2: LSST Prompt Processing Data Products

### LSST Prompt Data Products (Melissa Graham @ U. of Washington)

- Online LSST forum for DM [here](https://community.lsst.org/). See
  [ls.st/dmtn-102](ls.st/dmtn-102) for alert stream numbers.
- Alert production process:
  - New image reduced and calibrated
  - Difference image created
  - Source detection on difference image
  - Source association (by coordinate) and characterization
  - Alert packet assembled for SNR>5 detections
  - Alert sent to community
- Alert packet contents for 60s releases:
  - Difference image source parameters
    - ID, coordinate, flux, shape, SNR, association with static and moving cataloges
  - Difference image object parameters
    - ~12 month history of proper motion, parallax, mean flux, variability parameters,
      and ID for the latest Data Release deep stacks
  - Image stamps (FITS)
    - At least 6" by 6" with flux, variance, and mask extensions
    - Includes WCS, zero point, PSF, etc.
- You can request larger images than the postage stamp but there will be up to a 24hr
  delay waiting for the daily data release.
- May or may not have CCid information.
- Publication times start when image readout ends and broker access is allowed to
  initiate.
- LSST has its own basic filtering service so that users can submit basic queries (eg.
  SQL)
  - No cross-matching to other catalogs
  - No access to other LSST data products
  - A user can define a filter to go through alerts but can only receive a limited
    number of alerts. (Minimum of 20 full-size alerts per telescope visit out of 10,000
    generated per visit). Remember that alerts have a 12 month history. You can filter
    on this information.
  - Minimum of 100 simultaneous users filtering the stream, but the number is limited.

### Plans and Policies for LSST Alert Distribution (Eric Bellm @ U. of Washington)

- Key documents:
  - Plans and Policies for Alert Distribution (how will community brokers be chosen?)
    [ls.st/LDM-612](ls.st/LDM-612)
  - Data Products Definition Document LSE-163 (what will LSST alerts look like?)
    [ls.st/dpdd](ls.st/dpdd)
  - Call for Letters of Intent for Community Alert Brokers (how do I apply to be a
    community broker?) [ls.st/LDM-682](ls.st/LDM-682)
  - LSST Alerts: Key Numbers (how many? how much? how often?)
    [dmtn-102.lsst.io](dmtn-102.lsst.io)
- The number of community brokers will be finite.
  - Outbound bandwidth from the datacenter is the expected bottleneck; 10 Gbps allocated
    as a baseline
  - Current expectations for number of supported brokers is ~7
- Require demonstration of technical capability & appropriate personnel
  - No requirement to receive the full stream
  - No requirement to redistribute the full stream
  - No requirement to make products world public
  - Will favor proposals that offer these!
- The selection process has two phases: an open call for Letters of Intent, and an
  invitational call for full proposals.
- Brokers must demonstrate adequate resources
  - Large inbound and outbound network bandwidth (the full alert stream is a few
    TB/night)
  - Petabytes of disk capacity
  - Databases handling of billions of sources
  - Compute resources to handle sophisticated classification and filtering tasks in real
    time at scale
  - Appropriate personnel to develop and maintain the service Institutional & funding
    support to ensure the longevity and stability of the service.
- Brokers will be evaluated on their contribution to the scientific utilization of LSST.
  - Serve a large community
  - Enable high-profile science
  - Provide unique capabilities
  - Contribute to LSST’s four science pillars
  - Take advantage of the unique aspects of the LSST alert stream (real-time,
    world-public)
- Letters of intent due in May. Afterwords 3-day workshop, week of June 17, 2019,
  Seattle, WA Participants (by invitation) for LOI submitters and LSST Project personnel
- Letters of intent due May 15, 2019
  ([Submission template](https://github.com/lsst/LDM))
  - Proposals can still be in formative stages.
- ZTF
  - Alert Packet Tools: [https://zwicky.tf/4t5](https://zwicky.tf/4t5)
  - Alert Schema Documentation: [https://zwicky.tf/dm5](https://zwicky.tf/dm5)
  - Detailed Pipelines documentation: [https://zwicky.tf/ykv](https://zwicky.tf/ykv)
  - PASP instrument papers: [https://zwicky.tf/3w9](https://zwicky.tf/3w9)
- LSST
  - Data Products Definition Document: [ls.st/dpdd](ls.st/dpdd)
  - Prototype Schemas:
    [https://github.com/lsst-dm/sample-avro-alert](https://github.com/lsst-dm/sample-avro-alert)
  - Kafka-based Alert Stream:
    [https://github.com/lsst-dm/alert_stream](https://github.com/lsst-dm/alert_stream)
- Alert is around 82 KB
- ZTF alerts are available in bulk [here](https://ztf.uw.edu/alerts/public/)
- Example code for processing alerts is available [here](https://zwicky.tf/bq6)

## Thursday Session 3: Broker Components

### Connexions between LSST-DESC Broker and Machine Learning (Emille E. O. Ishida @ Université Clermont-Auvergne)

- Complete representation is not possible in astronomical training sets for machine
  learning (ML).
- One solution is to implement an active learning technique where human inspection is
  used to supplement the training process.
- This can be applied to multiple types of ML models.
- Human inspection does not scale to an online learning strategy with data sets as large
  as LSST. However it does provide a better training set for an initial, offline stage.
- This approach can bias you to a particular science case, and needs to be re-run for
  multiple science objectives.
- You can work in a "None of the above" category.

### RAPID - Real-time Automated Photometric IDentification (Daniel Muthukrishna @ University of Cambridge)

- Trained on PLAsTiCC data set.
- SN identification is very similar to voice analysis. Quiet followed by a sudden
  increase in signal on multiple frequencies.
- Publicly available via pip
- Designed to classify over time, updating classification percentages as more
  observations become available

## Thursday Session 4: Infrastructure in Development

### Antares (Gauthem):

- Classify objects, provide summary of object properties, and allow users to apply
  personalized filters
- Expected to scale easily to LSST
- Don't apply 1 ML model to find all objects. Train multiple models to find specific
  objects.
- Following LSST DM, ANTARES is dockarized
- RAPID training is built in.
- Thinking about google cloud and amazon for deployment.
- Uses SciServer and JupyterHub to provide a web front end.

### Lasair ()

- Backend development in place - still building front end api.
- Running on jupyter hub.
- Has half an exabyte of storage.

## Friday Session 5: Additional Talks and a Group Discussion on “Charting the Course Forward”

### NERSC support (Debbie Bard @ NERSC)

- Cori is generation NERSC-8. NERSC-9 (Perlmutter) comes online in 2020 and includes the
  addition of GPUs instead of just CPUs.
- NERSC 9 is targeted at data applications and simulations
- NVIDIA GPU-accelerated and AMD CPU only nodes
- Back end codes, including ML codes, will come optimized "out of the box" so users
  won't have to tune them.
- All flash file system increasing I/O speeds which is a big improvment fo ML which
  involves alot of random reads
- Spin is a side service running on seperate hardware for projects that don't need
  access to the full supercomputer resources (Jupyter, web interfaces, etc.).
  - Spin is where brokers will live.
  - Based on docker containers.

### PLAsTiCC update (Renae):

- Data and models will be made public

### SkyPortal (Stéfan van der Walt @ Berkely)

- Sky Portal is an open source data access portal
- Scalable from laptop to cloud services
- Dockerized
- Low overhead - fast - minimum mantinence
- Includes authentication and admin controls

## Random Thoughts

- Any broker system needs to have redundancies to protect against downtime
- Don't just build systems in advance - train people to use them in advance
- Brokers serve to simplify and filter data for easier consumption by the community.
  This can include a combination of rapid processing filters and slower, more indepth
  analysis.
- Finding objects is more than nightly image subtraction. You also apply models to find
  deviations from expected behavior.
- How to you encourage follow up data?
- Most brokers have a bias to specific science goals. This leaves room for a "None of
  the Above" broker.
- LSST templates for difference images will change annully. How to develop year 1
  templates is still being researched.
- The system should be dockerized
- Allow users to specify their own filters (on the entire stream) and watch lists (cuts
  on the area on the sky)
- There are publicly available ML classifiers that can be applied (eg. RAPID and
  PLAsTiCC).
- What "value added" products should we include? Look to existing brokers for
  inspiration.
- Log the version of each analysis step so you can track changes over time.
- SkyPortal can be used as a front end (more scalable, astronomy focused alternative to
  Flask, Django, etc...)
- Follow scheduler: https://tomtoolkit.github.io
- DESC doesn't want its own broker but is concerned about understanding the selection
  function and classification effeciency well.
