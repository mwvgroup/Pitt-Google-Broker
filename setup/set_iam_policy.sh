#! /bin/bash

# this is currently only implemented for pubsub topics
TOPIC="${1}"
ROLEID="${2:-projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic}"
USER="${3:-allUsers}"

# get the current policy
policy_yaml="current_policy_tmp.yml"
gcloud pubsub topics get-iam-policy "${TOPIC}" > "${policy_yaml}"

# append the binding
# if this is the first binding, we need a header
if [ $(grep "" -c $policy_yaml) -eq "1" ]; then
    echo "bindings:" >> "${policy_yaml}"
fi
echo "- role: ${ROLEID}" >> "${policy_yaml}"
echo "  members:" >> "${policy_yaml}"
echo "    - ${USER}" >> "${policy_yaml}"

# set the new policy on the project
gcloud pubsub topics set-iam-policy "${TOPIC}" "${policy_yaml}"

# cleanup
rm "${policy_yaml}"
