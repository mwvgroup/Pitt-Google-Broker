# Questions

- [ ] don't see any redshift info in alert_data['candidate']
- [ ] easier way to change DATA_DIR (download_data.py, parse_data.py)


# Notes and To Do
<!-- fs -->
[SDSS catalog](bruno/users/cnm37/Skyserver_3e5_stars_mags.csv, ~/Korriban/Documents/Pitt-Broker/mock_stream/data/Skyserver_3e5_stars_mags.csv)
- [x] rsync -avzn -e ssh tjr63@bruno.phyast.pitt.edu:pitt-broker/Skyserver_3e5_stars_mags.csv ~/Korriban/Documents/Pitt-Broker/mock_stream/data/.

moving data dir to Korriban:
- [x] rsync -avz /Users/troyraen/Documents/Pitt-Broker/mock_stream/data ~/Korriban/Documents/Pitt-Broker/mock_stream/

<!-- fe -->




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
