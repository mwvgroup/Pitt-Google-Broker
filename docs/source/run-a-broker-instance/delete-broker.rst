Delete the Broker
=================

To delete or "teardown" a broker instance means to permanently delete
all resources and data associated with that instance. Testing instances
should be deleted when they are no longer needed. Production instances
must be deleted manually; the automated script used below is
specifically configured to *prevent* their deletion. If you setup any
resources manually, the script used below does not know about them so
delete them manually.

.. code:: bash

    survey=ztf  # use the same survey used in broker setup
    testid=mytest  # use the same testid used in broker setup
    teardown=True

    # to use a local setup_broker.sh script, cd into the directory
    # cd Pitt-Google-Broker/broker/setup_broker

    # otherwise, download and use the script from the instance's bucket
    bucket="${GOOGLE_CLOUD_PROJECT}-${survey}-broker_files-${testid}"
    fsetup="setup_broker/setup_broker.sh"
    gsutil cp "gs://${bucket}/${fsetup}" .

    # delete everything associated with the instance
    ./setup_broker.sh "$testid" "$teardown" "$survey"
    # you will be prompted several times to confirm
