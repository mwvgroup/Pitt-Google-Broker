Accessing the ZTF Archive
=========================

All ZTF alerts are submitted at the end of the day to the `ZTF public alerts
archive`_. The ``ztf_archive`` module is capable of automatically downloading,
parsing, and plotting alert data that has been submitted to the public archive.
Alert data can only be downloaded in groups of daily data releases (i.e., you
cannot download individual alerts). The following code snippets demonstrate
how to download and access data from the ZTF archive.

Downloading From the Archive
----------------------------

Daily data releases can be downloaded from the ZTF archive individually or
iteratively in reverse chronological order.

.. code:: python

   from broker import ztf_archive as ztfa

   # Get a list of files available on the ZTF Alerts Archive
   print(ztfa.get_remote_release_list())

   # Download data from the ZTF archive for a given day.
   ztfa.download_data_date(year=2018, month=6, day=26)

   # Download the most recent day of available data
   ztfa.download_recent_data()

Although it is not recommended to download the entire alerts archive to your
local machine, it is an educational thought exercise to see a few different
cases of how this would work.

.. code:: python

   # Download all of the alerts and skip ones that have already been downloaded
   ztfa.download_recent_data(max_downloads=float('inf'))

   # Download all of the alerts while overwriting any existing data
   ztfa.download_recent_data(max_downloads=float('inf'))

   # Exit the function call once files are encountered that have already
   # been downloaded.
   ztfa.download_recent_data(max_downloads=float('inf'), stop_on_exist=True)

Accessing Local Alerts
----------------------

The ``ztf_archive`` module also provides functions for accessing and
visualizing alert data.

.. code:: python

   # Get a list of files downloaded from the archive
   print(ztfa.get_local_release_list())

   # Retrieve the IDs for all alerts downloaded to your local machine
   alert_ids = ztfa.get_local_alert_list()
   print(alert_ids)

   # Get data for a specific alert
   demo_id = alert_ids[0]
   alert_data = ztfa.get_alert_data(demo_id)

   # Plot image stamps used to generate the alert data
   fig = ztfa.plot_stamps(alert_data)
   fig.show()

In addition to acceding individual alerts by their ID value, you can iterate
over the entire set of downloaded alert data.

.. code:: python

   # Iterate over alerts one at a time
   for alert_list in ztfa.iter_alerts():
       # Some redundant task
       break

   # Or iterate over multiple alerts at once
   for alert_1, alert_2 in ztfa.iter_alerts(2):
       # Some other redundant task
       break

.. _ZTF public alerts archive: https://ztf.uw.edu/alerts/public/
