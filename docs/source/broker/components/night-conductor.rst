Night Conductor
===============

-  `What Does Night Conductor Do?`_
-  `Where to look if there's a problem`_

See also

-   :doc:`auto-scheduler`
-   :doc:`tracking-metadata.rst`
-   :doc:`../../broker/run-a-broker-instance/test-an-instance`

What Does Night Conductor Do?
-----------------------------

The night-conductor VM processes the Pub/Sub "counter" subscriptions, extracts metadata,
and stores it in BigQuery. See :doc:`tracking-metadata.rst`.

Night-conductor used to control the nightly start/stop of various broker components
(e.g., consumer), hence the name, but it doesn't do that anymore.

Where to look if there's a problem
----------------------------------

See :doc:`../../broker/run-a-broker-instance/view-resources` for details
like where to view logs, how to ssh into a VM, etc.

**Night Conductor's Logs**

Compare night conductor's logs with the scripts it runs. You probably
want to start with:

- vm\_startup.sh at the code path broker/night\_conductor/vm\_startup.sh
- start\_night.sh at the code path
  broker/night\_conductor/start\_night/start\_night.sh
- end\_night.sh at the code path broker/night\_conductor/end\_night/end\_night.sh

Remember that the actual scripts used by night conductor are stored in
its ``broker_files`` bucket. Fresh copies are downloaded to the VM prior
to execution.

You can also look at the logs from other resources.
