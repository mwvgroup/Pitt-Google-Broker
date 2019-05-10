Accessing the ZTF Archive
=========================

All ZTF alerts are submitted at the end of the day to the `ZTF public alerts
archive`_. The ``ztf_archive`` module is capable of automatically downloading,
parsing, and plotting alert data that has been submitted to the public archive.
Alert data can only be downloaded in groups of daily data releases (i.e. you
cannot download individual alerts). The following code snippet demonstrates
how to download and access data from the ZTF archive.

.. code:: python

   from broker import ztf_archive as ztfa

   # Get a list of files available on the ZTF Alerts Archive
   print(ztfa.get_remote_release_list())

   # Download data from the ZTF archive for a given day.
   ztfa.download_data_date(year=2018, month=6, day=26)

   # Get a list of downloaded files from the archive
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

   # Alternatively, you can iterate through alert data, 5 alerts at a time.
   # The ztfa.iter_alerts function yields a list of alert packets
   for alert_list in ztfa.iter_alerts(5):
       alert_ids = [alert['candid'] for alert in alert_list]
       print(alert_ids)
       break

.. _ZTF public alerts archive: https://ztf.uw.edu/alerts/public/
