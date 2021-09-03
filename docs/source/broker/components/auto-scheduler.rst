Auto-scheduler
==============

-  `Overview`_
-  `Cue-response checker`_ (checks that the
   broker responded appropriately to the auto-scheduler's cue.)

   -  `Alerting policy`_

See also:

-   :doc:`night-conductor`
-   :ref:`broker/components/night-conductor:Where to look if there's a problem`

Overview
--------

Broker ingestion of live topics is auto-scheduled with the following
process:

**Cloud Scheduler cron job -> Pub/Sub message -> Cloud Function ->
night-conductor VM startup**

The cron job sends a Pub/Sub message that simply contains the cue:
``START`` or ``END``. The Cloud Function receives the message, sets
appropriate metadata attributes on the night conductor VM and starts it.

(Note that you can start/stop the broker manually at any time by sending
a message to the auto-scheduler's Pub/Sub topic. See
:doc:`../../broker/run-a-broker-instance/run-broker`.)

Two cron jobs are scheduled, one each to start and end the night. Both
processes use the same Pub/Sub topic and Cloud Function.

Example: Change the time the broker auto-starts each night.

.. code:: bash

    survey=
    testid=
    jobname="${survey}-cue_night_conductor_START-${testid}"
    schedule='0 2 * * *'  # UTC. unix-cron format
    # https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules

    gcloud scheduler jobs update pubsub $jobname --schedule "${schedule}"

Example: Pause/resume the broker's auto-schedule.

.. code:: bash

    survey=
    testid=
    startjob="${survey}-cue_night_conductor_START-${testid}"
    endjob="${survey}-cue_night_conductor_END-${testid}"

    # pause the jobs
    gcloud scheduler jobs pause $startjob
    gcloud scheduler jobs pause $endjob

    # resume the jobs
    gcloud scheduler jobs resume $startjob
    gcloud scheduler jobs resume $endjob

By default, the cron jobs of a Testing instance are paused immediately
after creation so that the instance does not run automatically.

Cue-response checker
--------------------

The response checker Cloud Function is triggered by the auto-scheduler's
Pub/Sub topic (see above). It receives the auto-scheduler's cue and then
checks whether the broker responds appropriately. If the response is not
as expected, "Critical" errors are raised which trigger a GCP alerting
policy.

Alerting policy
~~~~~~~~~~~~~~~

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
