
# Use cases
<!-- fs -->
look in to [astrorapid](https://pypi.org/project/astrorapid/) for classification

## SN
What user wants:
    * Prob(SN type...)
    - selection function
    - host galaxy
        - mass
        - SFR
How to classify:
    - astrorapid
Primary catalogs to match on:
    - SDSS, maybe BOSS (northern sky)
    - DES (southern)
    - ZTF
XM features:
    * RA, DEC
    - classification
    - errors (more specifically... ?)
    - external survey depth
    - redshift

## CV (white dwarf with non-degen companion)
What user wants:
    * Prob(CV)
    - period
    - companion information
How to classify:
    - more light in xray than visible, but we probably won't have this info
    - check for existing ML or other algorithms
Primary catalogs to match on:
    - GAIA (more likely to contain companion than WD)
    - APOGEE (more likely to contain companion than WD)
    - Ritter & Kolb 2003 (CV catalog)
XM features:
    * RA, DEC
    - classification
    - errors (more specifically... ?)    

<!-- fe # Use cases -->


# Notes and To Do
<!-- fs -->

## July 9
<!-- fs -->
1. Have RAPID classifying SN with host galaxy info by July 23rd.
    * write it to accept dictionary as input (AVRO files are priority, but should be able to accept BigQuery input with some wrapper function.)
    - mwebv: milky way excess b-v color (dust extinction)
    - mjd: modified julian date
    - flux and error: convert PSF mags
    - zeropoint: magzpsci. ask Daniel
    - photflag: ask Daniel
2. Test pub/sub. Try to write automated tests.. input, calling fncs or code trying to test, and expected output.

<!-- fe ## July 9 -->

## RAPID
<!-- fs -->
[RAPID](https://astrorapid.readthedocs.io)
[ZTF Avro Schemas](https://zwickytransientfacility.github.io/ztf-avro-alert/schema.html)
Meeting prep:
* RAPID and SuperNNova
* RAPID more straightforward so setting that up.
    - but requires redshift info... standard process seems to be to use host gal redshift.
    - not sure what they do when there's no identified host.
* Need training dataset. Have galaxy set from Graham and SN, etc. set from PLAsTICC.
    - not sure if I'm allowed to use either for this purpose.



<!-- fe ## RAPID -->


## Testing pub_sub branch
<!-- fs -->
GCP topic: troy_test_topic
GCP subscription: troy_test_subscript

```python
from broker import ztf_archive as ztfa
# ztfa.download_data_date(year=2018, month=6, day=26)
ztfa.download_recent_data(max_downloads=10)

from google.cloud import pubsub_v1
project_id = 'ardent-cycling-243415'
topic_name = 'troy_test_topic'
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)
for n in range(1, 4):
    data = u'Message number {}'.format(n)
    # Data must be a bytestring
    data = data.encode('utf-8')
    # When you publish a message, the client returns a future.
    future = publisher.publish(topic_path, data=data)
    print('Published {} of message ID {}.'.format(data, future.result()))
print('Published messages.')

subscription_name = 'troy_test_subscript'
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_name)
max_messages = 10
response = subscriber.pull(subscription_path, max_messages=max_messages)
ack_ids = []
for received_message in response.received_messages:
    print("Received: {}".format(received_message.message.data))
    ack_ids.append(received_message.ack_id)
subscriber.acknowledge(subscription_path, ack_ids)
print("Received and acknowledged {} messages. Done.".format(len(ack_ids)))

# from pub_sub_client import message_service as ms
# ms.publish_alerts('pitt-broker', topic_name, alerts)
# alerts     (list): The list of ZTF alerts to be published (as returned by alert_acquistion.get_alerts())
# ms.subscribe_alerts('pitt-broker', subscription_name, max_alerts=1)

```
<!-- fe ## Testing pub_sub branch -->


## 6/11/19
<!-- fs -->
travel funding
use cases
data studio
<!-- fe ## 6/4/19 -->

## 6/4/19
<!-- fs -->
travel funding
use cases
data studio
<!-- fe ## 6/4/19 -->


## 5/28/19
<!-- fs -->
questions to answer:
planning to fail with Messier objects (15 arcmin)
what are our use cases
minimum viable product/protype
user watch list - (galactic variable stars, identified strong lensing systems, ) - could define own matching radius. Notify user of alert match and upcoming expected observations.
*want to set up user web interface*
    - list of alerts + value added
    - upcoming pointing regions
    - DIA object page
        - all related alerts
        - postage stamps
        - light curve: interactive, connect plot points to data tables
        - cross matches
            - whether spectra exist
        - classification confidence as a function of time
            - Ia, Ic, variable, AGN, galaxy
<!-- fe ## 5/28/19 -->

## 5/21/19
<!-- fs -->
1. choose a small handful of catalogs to focus on
    - SDSS (photometery and spectroscopy)
        - SEGUE (MW stars)
        - Sloan Supernova Survey (1a)
        - APOGEE (IR spec of MW stars)
        - BOSS and eBOSS (LRGs)
        - MaNGA (nearby galaxy spectroscopy)
    - WISE (IR all sky survey, near earth objects, star clusters) - ask Ross
    - GAIA (MW stars)
    - 2MASS (galaxies, star clusters, stars, galaxies behind MW, low mass stars)
    - Chandra Source Catalog (X-ray sources, AGN, SNe remnants, X-ray binaries)
2. evaluate store catalogs in Big Query
3. think about what we want to use in the xmatch
    - RA/DEC
    - redshift
    - object type/classification
    - photometery/colors
    - period
<!-- fe ## 5/21/19 -->

## April-ish 19
<!-- fs -->
[SDSS catalog](bruno/users/cnm37/Skyserver_3e5_stars_mags.csv, ~/Korriban/Documents/Pitt-Broker/mock_stream/data/Skyserver_3e5_stars_mags.csv)
- [x] rsync -avzn -e ssh tjr63@bruno.phyast.pitt.edu:pitt-broker/Skyserver_3e5_stars_mags.csv ~/Korriban/Documents/Pitt-Broker/mock_stream/data/.

moving data dir to Korriban:
- [x] rsync -avz /Users/troyraen/Documents/Pitt-Broker/mock_stream/data ~/Korriban/Documents/Pitt-Broker/mock_stream/
<!-- fe ## April-ish 19 -->

<!-- fe # Notes and To Do -->



# Questions

- [ ] don't see any redshift info in alert_data['candidate']
- [ ] easier way to change DATA_DIR (download_data.py, parse_data.py)

# GCP Account Info
Project name: pitt-google-broker-prototype
Project ID: ardent-cycling-243415
Project number: 591409139500

Service Account: tjraen-owner@ardent-cycling-243415.iam.gserviceaccount.com
project_id = 'ardent-cycling-243415'
topic_name = 'troy_test_topic'
subscription_name = 'troy_test_subscript'

# Code
<!-- fs -->

## Astroquery
<!-- fs -->
```python

# Get RA and DEC from alerts and write to file:
import pandas as pd
def get_alerts_RA_DEC(fout=None):
    """ Iterate through alerts and grab RA, DEC.
        Write data to file with format compatible with astroquery.xmatch.query().

        fout = string, path to save file.

        Returns the alert data as a Pandas DataFrame.
    """

    data_list = []
    for a, alert in enumerate(iter_alerts()):
        alert_id = alert['candid']
        alert_data = get_alert_data(alert_id)

        dat = {}
        dat['alert_id'] = alert_id
        dat['ra'] = alert_data['candidate']['ra']
        dat['dec'] = alert_data['candidate']['dec']
        data_list.append(dat)

        if a>1000: break

    print('creating df')
    df = pd.DataFrame(data_list)

    if fout is not None:
        print('writing df')
        df.to_csv(fout, sep=',', columns=['alert_id','ra','dec'], header=True, index=False)
    else:
        return df

    return None

fradec = 'mock_stream/data/alerts_radec.csv'
get_alerts_RA_DEC(fout=fradec)

# Use Astroquery to query CDS xMatch service
from astropy import units as u
from astroquery.xmatch import
table = XMatch.query(cat1=open(fradec), cat2='vizier:II/246/out', \
                    max_distance=5 * u.arcsec, colRA1='ra', colDec1='dec')
# with the current data, this matches 818 out of 1002 in fradec
# table.columns gives ['angDist','alert_id','ra','dec','2MASS','RAJ2000','DEJ2000','errHalfMaj','errHalfMin','errPosAng','Jmag','Hmag','Kmag','e_Jmag','e_Hmag','e_Kmag','Qfl','Rfl','X','MeasureJD']

```

<!-- fe Astroquery -->



## Download and look at alerts
<!-- fs -->
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
download_data(max_downloads=1)

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
alert_id = 833156294815015029
alert_data = get_alert_data(alert_id)
RA, DEC = alert_data['candidate']['ra'], alert_data['candidate']['dec']
# print(alert_data)


# Plot stamp images for alert data
fig = plot_stamps(alert_data)
plt.show()

```
<!-- fe download and look at alerts -->

<!-- fe -->


# DESC call re: LSST call for brokers (4/10/19)
<!-- fs -->
[Official Notes](https://docs.google.com/document/d/1hsQd4JDPgscUkGEw6m8qL_Fxy8JyRvMSBYHzDePXlMc/edit)

No DESC working groups have expressed need for alerts on timescales < 24 hours
    => no driver for DESC to develop a broker
One thing DESC needs that is not part of 60sec alert stream is..?

Value added products DESC needs:
    - classify events scientifically
    - triggering followup

LSST considering offering alert stream in cloud.

DESC will focus on 24hr and yearly data releases.

__Useful quality of Broker: _light_ filtering of alerts__


<!-- fe DESC call re: LSST call for brokers -->
