# Broker Instance Keywords

- [Keywords](#keywords)
    - [Resource Names](#resource-names)
    - [Production vs Testing Instances](#production-vs-testing-instances)

---

Multiple instances of the broker can run in parallel, differentiated by their keywords.
This allows us to (1) ingest and process different surveys, and (2) develop and test the broker software.

## Keywords

The keywords of a given broker instance serve two purposes: (1) they tie together the instance's resources, and (2) they determine the schema used to process the data. The keywords are:

- __survey__: `ztf` or `decat`. Name of the survey stream the instance ingests.
This keyword (1) is prepended to the names of all instance resources, and (2) determines the schema used to process the data. It also triggers some schema-related differences in behavior, particularly in the science processing pipeline.

- __testid__: string of lowercase letters and numbers, beginning with a letter.
This keyword is appended to the names of all instance resources.
Its purpose is to differentiate broker instances that are processing the same survey.
This allows us to run a broker instance "in production" alongside others used in development and testing, without the instances interfering with each other.
If the testid is `False`, nothing gets appended to the resource names, and we call the instance a "production" instance.


### Resource Names

All resources have a __name stub__ that we use to generically identify the resource, independent of the particular broker instance.
See [Broker Overview](broker-overview.md) for a list.
For example, the name stub of the consumer VM is `consumer`.
The names of resources belonging to a given broker instance will have the survey prepended and the testid appended (unless the testid is `False`, in which case it is omitted).
The character `-` separates the stub from the keywords, except in rare cases (BigQuery datasets) where it is restricted by GCP naming rules, and then `_` is used.
So a broker instance set up with `survey = 'ztf'` and `testid = 'mytestid'` will have a consumer VM named `ztf-consumer-mytestid`.

Note that Cloud Storage buckets also have the project ID prepended, for uniqueness across GCP.


### Production vs Testing Instances

- "Production" instances are identified with `testid = False`. Their resources do not have a testid appended. For example, the consumer VM would be named `ztf-consumer`.
The `setup_broker.sh` script will not teardown (delete) a production instance, this would need to be done manually.
This helps prevent accidental deletion of the main broker instance (and all related resources and data) ingesting a particular survey.

- "Testing" instances refer to all brokers that are not production instances.
