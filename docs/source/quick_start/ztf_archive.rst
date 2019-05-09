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

   # Download recent data from the ZTF archive.
   # Note: Daily releases can be as large as several Gb
   ztfa.download_data()

   # Retrieve the number of daily releases that are locally available
   print(ztfa.get_number_local_releases())

   # Retrieve the number of alerts that have been downloaded
   # from all combined daily releases.
   print(ztfa.get_number_local_alerts())

   # Iterate through alert data, 5 alerts at a time.
   # The ztfa.iter_alerts function yields a list of alert packets
   for alert_list in ztfa.iter_alerts(5):
       alert_ids = [alert['candid'] for alert in alert_list]
       print(alert_ids)
       break

   # Alternatively, you can also get data for a specific alert id
   alert_data = ztfa.get_alert_data(alert_id[0])
   print(alert_data)

   # Plot image stamps used to generate the alert data
   fig = plot_stamps(alert_data)
   fig.show()

.. _ZTF public alerts archive: https://ztf.uw.edu/alerts/public/
