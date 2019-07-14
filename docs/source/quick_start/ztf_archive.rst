Accessing the ZTF Archive
=========================

All public ZTF alerts are submitted at the end of the day to the `ZTF public
alerts archive`_. The ``ztf_archive`` module is capable of automatically
downloading, parsing, and plotting alert data that has been submitted to the
public archive. Alert data can only be downloaded in groups of daily data
releases (i.e., you cannot download individual alerts). The following code
snippets demonstrate how to download and manipulate data from the ZTF archive.

Downloading From the Archive
----------------------------

Daily data releases can be downloaded from the ZTF archive individually or
iteratively in reverse chronological order.

.. code:: python

   from broker import ztf_archive as ztfa

   # Get a list of files available on the ZTF Alerts Archive
   file_names, file_sizes = ztfa.get_remote_md5_table()
   print(file_names)

   # Download data from the ZTF archive for a given day.
   ztfa.download_data_date(year=2018, month=6, day=26)

   # Download the most recent day of available data
   ztfa.download_recent_data(max_downloads=1)

   # Delete any data downloaded to your local machine
   ztfa.delete_local_data()


Accessing Local Alerts
----------------------

The ``ztf_archive`` module also provides functions for accessing and
visualizing alert data.

.. code:: python

   # Retrieve the IDs for all alerts downloaded to your local machine
   alert_ids = ztfa.get_local_alert_list()
   print(alert_ids)

   # Get data for a specific alert
   demo_id = alert_ids[0]
   alert_data = ztfa.get_alert_data(demo_id)

   # Plot image stamps used to generate the alert data
   fig = ztfa.plot_stamps(alert_data)
   fig.show()

In addition to accessing individual alerts by their ID value, you can iterate
over the entire set of downloaded alert data.

.. code:: python

   # Iterate over alerts one at a time
   for alert_list in ztfa.iter_alerts():
       # Some redundant task
       break

   # Or iterate over multiple alerts at once
   for alert_list in ztfa.iter_alerts(100):
       # Some other redundant task
       break

.. _ZTF public alerts archive: https://ztf.uw.edu/alerts/public/


Synchronizing with GCP
----------------------

Instead of dealing with archive data on your local machine, you can use the
GCP File Transfer Service to upload a table of files from ZTF directly into
a storage bucket (see here for more information). This table can be generated
automatically using the ``create_ztf_sync_table`` function. If the name of an
existing GCP bucket is provided, then any ZTF release files already present
in the bucket are ignored.

.. code:: python

   # Handle the table programatically
   sync_table = create_ztf_sync_table('my_bucket')

   # Or save the results to a txt file
   sync_table = create_ztf_sync_table('my_bucket', 'out_file.txt')
