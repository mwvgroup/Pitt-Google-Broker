When you are done with it, please teardown (delete) your testing instance of the broker.
See below for the specific code, but essentially you execute the `setup_broker.sh` script with the `teardown` flag set to `True`.

The "teardown" options that can be triggered in the setup scripts are specifically configured to _prevent_ a user from deleting _production_ resources, even if the user intentionally tries to do so.
This is one layer of security, but we should still look into protecting those resources in other ways (e.g., make backups of databases and buckets, find out which resources can be configured directly to prevent deletion and configure them).


## 3b. Teardown the testing instance

When you are completely done with your testing instance of the broker, __delete it__ by running the broker's setup script with the "teardown" argument set to `True`.

```bash
cd Pitt-Google-Broker/broker/setup_broker

# Teardown/delete all test resources with the testid "mytest"
testid="mytest"
teardown="True"
./setup_broker.sh $testid $teardown
```

This will delete all GCP resources tagged with the testid. You will be prompted several times to confirm.
