Onboard a new developer
=======================

.. Developer instructions
.. ----------------------
..
.. Complete the instructions in the initial setup tutorial
.. (ref:`docs/source/broker/initial-setup/initial-setup`).
..
.. You will need to do this in conjunction with a Pitt-Google project manager so that they can grant you the necessary permissions.
..
.. You will need to provide the manager with both your Google account email address (e.g., Gmail address) and your service account name (which you will choose during setup).

Project manager instructions
----------------------------

Note this needs to be done in conjunction with the developer's setup.
The developer needs permissions (a role) bound to their Google account in order to create a service account, and the service account must exist before we can bind a role to it.

Setup
^^^^^

Set GCP environment variables and authenticate yourself to the GCP project that the developer needs access to (probably the testing project).
For reference, our current projects are:


* production project: ``ardent-cycling-243415``
* testing project: ``avid-heading-329016``

.. code-block:: bash

   # Set environment variables
   # fill these in with your values; they are used throughout
   export GOOGLE_CLOUD_PROJECT=<project_id>
   export GOOGLE_APPLICATION_CREDENTIALS=<path/to/GCP_auth_key.json>

   # Authenticate to use gcloud tools in this project
   gcloud auth activate-service-account \
       --project="${GOOGLE_CLOUD_PROJECT}" \
       --key-file="${GOOGLE_APPLICATION_CREDENTIALS}"

Set some variables defining the user account(s) and role.

.. code-block:: bash

   # fill in the user's Google account email address (e.g., Gmail address):
   user_email=

   # fill in the user's service account name and set the email address
   service_account_name=
   service_account_email="${service_account_name}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

   # choose a role_id (one eample is commented out below), and set the role
   role_id=
   # role_id="developerStudent"
   role="projects/${GOOGLE_CLOUD_PROJECT}/roles/${role_id}"
   # the above syntax is for a custom role that we've defined in the project
   # you can also use a predefined role. see the reference link given above for all options
   # role="role/viewer"

Onboard a developer
^^^^^^^^^^^^^^^^^^^

Add two policy bindings; one for the user's Google account (e.g., Gmail address, used for console access, etc.) and one for the user's service account (used to make API calls).

.. code-block:: bash

   gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
       --member="user:${user_email}" \
       --role="${role}"

   # the service account needs to exist before
   # we can run this command to bind the policy
   gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
       --member="serviceAccount:${service_account_email}" \
       --role="${role}"

Offboard a developer
^^^^^^^^^^^^^^^^^^^^

Follow the setup instructions above to set variables, then remove both policy bindings:

.. code-block:: bash

   gcloud projects remove-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
       --member="user:${user_email}" \
       --role="${role}"

   gcloud projects remove-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
       --member="serviceAccount:${service_account_email}" \
       --role="${role}"
