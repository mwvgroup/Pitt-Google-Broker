Configuring Travis
==================

This section of the documentation outlines how to configure
continuous-integration testing on `travis-ci.com
<https://www.travis-ci.com/>`_. A `.travis.yml` configuration file is already
included in the project's official `GitHub repository`_. However, you will
also need to add your GCP authentication keys to your travis environment
so that GCP services can be accessed during testing.

.. note:: For a more extensive overview of this process, feel free to
   reference the `official Google Docs`_

The Travis CLI Tool
-------------------

The ``travis`` command line tool is required to configuring Google Could
authentication when using continuous integration on
`travis-ci.com <https://www.travis-ci.com/>`_.
The travis command line tool can be installed using ``gem``:

.. code-block:: bash

   sudo gem install travis

Certain versions of Mac OSX include System Integrity Protection (SIP) which
effects the installation of packages that use the default Ruby install
(including `travis`). If using OS X El Capitan or later, you may need to
install the commandline tool using:

.. code-block:: bash

   sudo gem install -n /usr/local/bin/ travis

Once `travis` is installed, login to your user account.

.. code-block:: bash

   travis login --pro

Downloading Credentials
-----------------------

To begin, create a new service account for running continuous-integration tests
on the `Iam Service Accounts`_ page. Once done, download the JSON
authentication key and put it in a safe place.

You will also need to create a new API key from the `API Credentials`_ page.
Using your API key, create a file ``api_key.py`` that contains the following
single line:

.. code-block:: python

   key = '[YOUR-API-KEY]'


Encrypting Credentials
----------------------

Create a ``tar`` archive file that contains the your credential files and
encrypt the archive using the ``travis`` command line tool:

.. code-block:: bash

   tar -czf credentials.tar.gz client-secret.json api_key.py
   travis encrypt-file credentials.tar.gz --pro
   rm credentials.tar.gz  # Remove unencryted file so it's not accidentally committed to GitHub

The encryption command above will print a command that starts with
``openssl aes-256-cbc``. This is the command to decrypt the authentication
data. Copy the decryption command and add it to the travis config
file (`.travis.yml`) as well as a command to decompress the authentication
files. The following is provided as an example:

.. code-block:: yaml

   before_install:
     - openssl aes-256-cbc -K $encrypted_***_key -iv $encrypted_***_iv -in credentials.tar.gz.enc -out credentials.tar.gz -d
     - tar xvf credentials.tar.gz

Saving Your Results
-------------------

Add the encrypted archive of credentials to your project repository:

.. code-block:: bash

   git add credentials.tar.gz.enc .travis.yml
   git commit -m "Adds gcp authentication for travis"

Finally, delete any unencrypted copies of your authentication data or move it
to a secure location if it is not already there.

.. _API Credentials: https://console.cloud.google.com/project/_/apiui/credential
.. _GitHub Repository: https://github.com/mwvgroup/Pitt-Google-Broker
.. _Iam Service Accounts: https://console.cloud.google.com/iam-admin/serviceaccounts
.. _official Google Docs: https://cloud.google.com/solutions/continuous-delivery-with-travis-ci