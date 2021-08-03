Cross Matching Targets
======================

The ``xmatch`` module provides target crossmatching of observed targets
against the Vizier catalog service.

.. code:: python

   from broker import xmatch as xm

   # Write a CSV file with RA, DEC:
   ra_dec_path = 'mock_stream/data/alerts_radec.csv'
   xm.get_alerts_ra_dec(fout=ra_dec_path)

   # Query VizieR for cross matches:
   xm_table = xm.get_xmatches(fcat1=ra_dec_path, cat2='vizier:II/246/out')
   print(xm_table)
