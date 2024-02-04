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


Uptime Check Schedules
----------------------

.. note::

    The following setup is cumbersome and has the further disadvantage that it has
    to be scheduled separately from the VMs. Fixing it is part of
    `#109 <https://github.com/mwvgroup/Pitt-Google-Broker/issues/109>`__.

The Cloud Function ``check_cue_response`` checks whether instances are running or
terminated, as appropriate for the time of day.

The process looks like this:

Cloud Scheduler cron job -> Pub/Sub message -> Cloud Function

The cron job sends a Pub/Sub message that simply contains the cue:
``START`` or ``END``. The Cloud Function receives the message, and checks whether the
VMs are either running or stopped, as expected.
If the response is not as expected, "Critical" errors are raised which trigger a GCP
alerting policy.
By default, the cron jobs of a Testing instance are paused immediately
after creation.

Alerting policy
---------------

An alerting policy was created manually to notify Troy Raen of anything
written to the log named ``check-cue-response-cloudfnc`` that has
severity ``'CRITICAL'``. Every broker instance has a unique
``check_cue_response`` Cloud Function, but they all write to the same
log. Therefore, a new policy does not need to be created with each new
broker instance. (Also, recall that the auto-scheduler is typically only
active in Production instances.)

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

All broker instances share the following logs:

- `check-cue-response-cloudfnc <https://cloudlogging.app.goo.gl/525hswivBiZfZQEUA>`__
