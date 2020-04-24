Configuring Travis
==================

1. Create a ``tar`` archive file that contains the your credential files and encrypt the archive using travis

.. code-block:: bash

   tar -czf credentials.tar.gz client-secret.json api_key.py
   travis encrypt-file credentials.tar.gz --pro
   rm credentials.tar.gz  # Remove unencryted file so it's not accidentally committed to GitHub

2. The encryption command will output a command that starts with ``openssl aes-256-cbc``. Copy this command and save it for the next step.

3. Update the travis config file (`.travis.yml`) to include the decryption command you copied earlier as well as a command to decompress the authentication files.

.. code-block:: yaml

   before_install:
     - openssl aes-256-cbc -K $encrypted_***_key -iv $encrypted_***_iv -in credentials.tar.gz.enc -out credentials.tar.gz -d
     - tar xvf credentials.tar.gz


4. Finally, add the encrypted archive of credentials to the repository:

.. code-block:: bash

   git add credentials.tar.gz.enc .travis.yml
   git commit -m "Adds gcp authentication for travis"


