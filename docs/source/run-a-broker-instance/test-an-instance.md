# Workflow: Running, Developing, and Testing a Broker Instance

__Prerequisites:__
1. Complete the [Initial Setup](initial-setup.md) for GCP and your local environment.
2. Create a broker instance by following [Setup the Broker](setup-broker.md).

---

__Workflow:__
1. [Start the broker instance](run-broker.md#start-the-broker) with the attribute `KAFKA_TOPIC` set to `NONE`. This will start up everything except the consumer VM. Dataflow jobs will not receive alerts published before they start, so make sure they've started.
2. Run the [consumer simulator](consumer-simulator.md).
3. Make code changes and updates to the instance components, as desired.
4. Repeat steps 2 and 3, as desired.
5. [Stop the broker instance](run-broker.md#stop-the-broker).

See also:
- [View and Access Resources](view-resources.md)

---

__Cleanup:__
1. When you are completely done with the broker instance, delete it by following [Delete the Broker](delete-broker.md).
