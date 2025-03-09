#! /bin/bash
# Build the image, create ancillary resources, and deploy the module as a Cloud Run service.
#
# --------- Example usage -----------------------
#   First, double check the values in env.yaml. Then:
# $ gcloud auth ...
# $ export PROJECT_ID=... (is this set automatically by gcloud auth?)
# $ bash deploy.sh
# -----------------------------------------------

# --------- Set environment variables -----------
# Load env.yaml and set the key/value pairs as environment variables.
# [FIXME] This depends on yq. We need to provide instructions for installing it
#         or else just have the user export these manually.
while IFS='=' read -r key value; do
  export "$key=$value"
done < <(yq -r 'to_entries | .[] | .key + "=" + .value' env.yaml)

# Ensure that all required environment variables are set.
check_env_vars() {
  local vars=("$@")
  for var in "${vars[@]}"; do
    if [ -z "${!var}" ]; then
      echo "Error: ${var} environment variable is not set."
      exit 1
    fi
    export "_${var}="
  done
}
check_env_vars PROJECT_ID _SURVEY _TESTID MODULE_NAME_STEM MODULE_ROUTE REGION REPOSITORY_STEM TRIGGER_TOPIC_STEM

# Construct and export additional environment variables for cloudbuild.yaml.
# Environment variables that will be used by cloudbuild.yaml must start with "_", per GCP's requirements.
export _MODULE_NAME=$(construct-name.sh --stem "$MODULE_NAME_STEM")
export _REPOSITORY=$(construct-name.sh --stem "$REPOSITORY_STEM")
export _TRIGGER_TOPIC=$(construct-name.sh --stem "$TRIGGER_TOPIC_STEM")
# -----------------------------------------------

# --------- Project setup -----------------------
# [FIXME] This is a project setup task, so should be moved to a script dedicated to that.
# Ensure the Cloud Run service has the necessary permissions.
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud run services add-iam-policy-binding "${_MODULE_NAME}" \
    --member="serviceAccount:${runinvoker_svcact}" \
    --role="roles/run.invoker"
# -----------------------------------------------

# --------- Build -------------------------------
# Execute the build steps.
echo "Executing cloudbuild.yaml..."
moduledir=$(dirname "$(readlink -f "$0")")  # Absolute path to the parent directory of this script.
url=$(gcloud builds submit \
    --config="${moduledir}/cloudbuild.yaml" \
    --region="${REGION}" \
    "${moduledir}" | sed -n 's/^Step #2: Service URL: \(.*\)$/\1/p'
)
# -----------------------------------------------

# --------- Finish build ------------------------
# [FIXME] Figure out how to include this in cloudbuild.yaml. It is here because we need the value of $url.
# Create the subscription that will trigger the Cloud Run service.
echo "Creating trigger subscription for Cloud Run..."
# [FIXME] Handle these retries better.
echo "WARNING: This is set to retry failed deliveries. If there is a bug in main.py this will"
echo "         retry indefinitely, until the message is delete manually."
trigger_subscrip="$_TRIGGER_TOPIC"
gcloud pubsub subscriptions create "${trigger_subscrip}" \
    --topic "${_TRIGGER_TOPIC}" \
    --topic-project "${PROJECT_ID}" \
    --ack-deadline=600 \
    --push-endpoint="${url}${MODULE_ROUTE}" \
    --push-auth-service-account="${runinvoker_svcact}"
# -----------------------------------------------
