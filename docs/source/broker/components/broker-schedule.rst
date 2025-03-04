Broker Schedule
===============

-  `VM Schedules`_
-  `Uptime Check Schedules`_
-  `Alerting policy`_

VM Schedules
------------

The consumer VM is scheduled to start each night and stop each morning using a resource
policy. The schedule is set when the VM instance is created.
The schedule is disabled in testing instances.
To view or update the schedule, see
:ref:`View and Access Resources: Compute Engine VMs <broker/run-a-broker-instance/view-resources:Compute Engine VMs>`
To manually start/stop an instance, see
:ref:`Run the Broker <broker/run-a-broker-instance/run-broker>`.


Alerting policy
---------------

To update the existing policy, or create a new one, see:

-   `Managing log-based alerts
    <https://cloud.google.com/logging/docs/alerting/log-based-alerts>`__
-   `Managing alerting policies by API
    <https://cloud.google.com/monitoring/alerts/using-alerting-api>`__
-   `Managing notification channels
    <https://cloud.google.com/monitoring/support/notification-options>`__

Where to look if there's a problem
----------------------------------

See :doc:`../../broker/run-a-broker-instance/view-resources` for details
like where to view logs, how to ssh into a VM, and where to view
Dataflow jobs on the GCP Console.

Auto-scheduler's Logs
~~~~~~~~~~~~~~~~~~~~~
