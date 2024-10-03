# Setup broker using Terraform

## Organizational thoughts

1. create .tf files: decide whether to do these per resource or per GCP service
2. create Modules: one per component, plus one for the full broker

## Links

- [Terraform Modules](https://www.terraform.io/language/modules/develop)
- [Terraform - Google Modules](https://github.com/terraform-google-modules)
- [Terraform - Google reference](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/pubsub_topic_iam#google_pubsub_topic_iam_member)
- [Terraform - Cloud Functions reference](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloudfunctions_function)

## Create starter files

Have gcloud crawl our project and create some starter files for us.

```bash
dir="broker/setup_broker/terraform/pitt-google-broker-prototype"

gcloud beta resource-config bulk-export --project="${GOOGLE_CLOUD_PROJECT}" \
    --resource-format=terraform \
    --path="${dir}"
```
