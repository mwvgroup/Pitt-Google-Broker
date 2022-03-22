# IAM Resources<a name="iam-resources"></a>

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [IAM Resources](#iam-resources)
  - [Setup](#setup)
  - [Roles](#roles)
    - [Create the roles](#create-the-roles)
    - [Update a role](#update-a-role)
  - [Policies](#policies)
    - [Set the policy on the project](#set-the-policy-on-the-project)
    - [Set a policy on a specific resource](#set-a-policy-on-a-specific-resource)
  - [Onboard a new developer](#onboard-a-new-developer)
    - [Developer instructions](#developer-instructions)
    - [Project manager instructions](#project-manager-instructions)
    - [Offboard a developer](#offboard-a-developer)

<!-- mdformat-toc end -->

Basic idea:

We need to connect three things: resource(s), permission(s), and user(s).

1. Create a Role - this is a collection of permissions and is a registered resource in GCP.
1. Create a Policy - this is a local file that defines a collection of bindings (bindings attach roles to members)
1. Attach the Policy to the Project, or to a specific Resource - access will be restricted this restricts access to the resource according to the policy. Policies can be attached to projects, and therefore apply to all resources in the project.

Helpful links:

- [IAM overview](https://cloud.google.com/iam/docs/overview)
- [IAM predefined roles reference](https://cloud.google.com/iam/docs/understanding-roles#predefined)
- [IAM permissions reference](https://cloud.google.com/iam/docs/permissions-reference)

## Setup<a name="setup"></a>

Set GCP environment variables and authenticate yourself
For reference, our current projects are:

- production project: `ardent-cycling-243415`
- testing project: `avid-heading-329016`

```bash
# Set environment variables
# fill these in with your values; they are used throughout
export GOOGLE_CLOUD_PROJECT=<project_id>
export GOOGLE_APPLICATION_CREDENTIALS=<path/to/GCP_auth_key.json>

# Authenticate to use gcloud tools in this project
gcloud auth activate-service-account \
    --project="${GOOGLE_CLOUD_PROJECT}" \
    --key-file="${GOOGLE_APPLICATION_CREDENTIALS}"
```

## Roles<a name="roles"></a>

### Create the roles<a name="create-the-roles"></a>

```bash
# To Do:
# get the organization id (not project id)
# for role_yaml in roles:
# read role_id from file, then:
role_id=developerStudent
role_yaml=roles/developer_student.yaml
gcloud iam roles create $role_id --project=$GOOGLE_CLOUD_PROJECT --file=$role_yaml
```

### Update a role<a name="update-a-role"></a>

(simpler in python so you don't have to mess with the etag fingerprint)

```python
# this is an untested example from the following url
# https://cloud.google.com/iam/docs/creating-custom-roles
def edit_role(name, project, title, description, permissions, stage):
    """Creates a role."""

    # pylint: disable=no-member
    role = service.projects().roles().patch(
        name='projects/' + project + '/roles/' + name,
        body={
            'title': title,
            'description': description,
            'includedPermissions': permissions,
            'stage': stage
        }).execute()

    print('Updated role: ' + role['name'])
    return role
```

## Policies<a name="policies"></a>

We should set the project policy when the project is created.
Afterwards, add or remove bindings to the policy individually (see onboarding section below for an example) rather than using the instructions in this section (which set the policy as a whole).

### Set the policy on the project<a name="set-the-policy-on-the-project"></a>

This binds member-role pairs to every resource in the project. (See below to bind to a specific resource.)

We must download the current policy, update the file and use it to set a new policy.
Setting a policy overrides the current policy.

```bash
policy_file="current_policy.yaml"
gcloud projects get-iam-policy $GOOGLE_CLOUD_PROJECT >> $policy_yaml
# update the bindings in the policy_file as needed, then set a new policy
gcloud projects set-iam-policy $GOOGLE_CLOUD_PROJECT $policy_yaml
```

### Set a policy on a specific resource<a name="set-a-policy-on-a-specific-resource"></a>

(simpler in python so you don't have to mess with the etag fingerprint)

```python
# this is an example from
# https://cloud.google.com/pubsub/docs/access-control#python_2
from google.cloud import pubsub_v1

# TODO(developer): Choose an existing subscription.
# project_id = "your-project-id"
# subscription_id = "your-subscription-id"

client = pubsub_v1.SubscriberClient()
subscription_path = client.subscription_path(project_id, subscription_id)

policy = client.get_iam_policy(request={"resource": subscription_path})

# Add all users as viewers.
policy.bindings.add(role="roles/pubsub.viewer", members=["domain:google.com"])

# Add a group as an editor.
policy.bindings.add(role="roles/editor", members=["group:cloud-logs@google.com"])

# Set the policy
policy = client.set_iam_policy(
    request={"resource": subscription_path, "policy": policy}
)

print("IAM policy for subscription {} set: {}".format(subscription_id, policy))

client.close()
```

## Onboard a new developer<a name="onboard-a-new-developer"></a>

The following instructions are left for reference, but these are in the docs (directory: docs/source/broker/initial-setup/) and should be kept up-to-date there.

### Developer instructions<a name="developer-instructions"></a>

Complete the instructions in the initial setup tutorial
(docs/source/broker/initial-setup/initial-setup.rst).

You will need to do this in conjunction with a Pitt-Google project manager so that they can grant you the necessary permissions.

You will need to provide the manager with both your Google account email address (e.g., Gmail address) and your service account name (which you will choose during setup).

### Project manager instructions<a name="project-manager-instructions"></a>

Make sure you've authenticated with the GCP project that the developer needs access to (see [Setup](#setup)).

Note this needs to be done in conjunction with the developer's setup.
The developer needs permissions (a role) bound to their Google account in order to create a service account, and the service account must exist before we can bind a role to it.

Setup:

```bash
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
```

Add two policy bindings; one for the user's Google account (e.g., Gmail address, used for console access, etc.) and one for the user's service account (used to make API calls).

```bash
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="user:${user_email}" \
    --role="${role}"

# the service account needs to exist before
# we can run this command to bind the policy
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="serviceAccount:${service_account_email}" \
    --role="${role}"
```

### Offboard a developer<a name="offboard-a-developer"></a>

Follow the setup in [Project manager instructions](#project-manager-instructions), then remove both policy bindings:

```bash
gcloud projects remove-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="user:${user_email}" \
    --role="${role}"

gcloud projects remove-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="serviceAccount:${service_account_email}" \
    --role="${role}"
```
