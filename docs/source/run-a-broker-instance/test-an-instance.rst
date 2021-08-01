Workflow: Run/Develop/Test a Broker Instance
============================================

**Prerequisites:**

1. Complete the :doc:`initial-setup` for GCP and your local environment.
2. Create a broker instance by following :doc:`setup-broker`.

--------------

**Workflow:**

1. :ref:`run-a-broker-instance/run-broker:start the broker` with the attribute
   ``KAFKA_TOPIC`` set to ``NONE``. This will start up everything except
   the consumer VM. Dataflow jobs will not receive alerts published before
   they start, so make sure they've started.
2. Run the :doc:`consumer-simulator`.
3. Make code changes and updates to the instance components, as desired.
4. Repeat steps 2 and 3, as desired.
5. :ref:`run-a-broker-instance/run-broker:stop the broker`.

See also: :doc:`view-resources`

--------------

**Cleanup:**

1. When you are completely done with the broker instance,
delete it by following :doc:`delete-broker`.
