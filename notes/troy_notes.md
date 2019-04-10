# Questions

- [ ] don't see any redshift info in alert_data['candidate']


# Notes and To Do
<!-- fs -->
[SDSS catalog](bruno/users/cnm37/Skyserver_3e5_stars_mags.csv, ~/Korriban/Documents/Pitt-Broker/mock_stream/data/Skyserver_3e5_stars_mags.csv)
- [x] rsync -avzn -e ssh tjr63@bruno.phyast.pitt.edu:pitt-broker/Skyserver_3e5_stars_mags.csv ~/Korriban/Documents/Pitt-Broker/mock_stream/data/.

moving data dir to Korriban:
- [x] rsync -avz /Users/troyraen/Documents/Pitt-Broker/mock_stream/data ~/Korriban/Documents/Pitt-Broker/mock_stream/

<!-- fe -->


# Code
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
alert_id = 792268253815010015
alert_data = get_alert_data(alert_id)
RA, DEC = alert_data['candidate']['ra'], alert_data['candidate']['dec']
# print(alert_data)


# Plot stamp images for alert data
fig = plot_stamps(alert_data)
plt.show()

```

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
