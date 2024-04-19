# docs/source/working-notes/troyraen/cloudbuild.md

## Cloud Build

- [Overview of Cloud Build](https://cloud.google.com/build/docs/overview)
- [Build configuration file schema](https://cloud.google.com/build/docs/build-config-file-schema)
    - [Substituting variable values](https://cloud.google.com/build/docs/configuring-builds/substitute-variable-values)

Example Build config (yaml) file structure:

```yaml
steps:
- name: string
  args: [string, string, ...]
  env: [string, string, ...]
  dir: string
  id: string
  waitFor: [string, string, ...]
  entrypoint: string
  secretEnv: string
  volumes: object(Volume)
  timeout: string (Duration format)
- name: string
  ...
- name: string
  ...
timeout: string (Duration format)
queueTtl: string (Duration format)
logsBucket: string
options:
 env: [string, string, ...]
 secretEnv: string
 volumes: object(Volume)
 sourceProvenanceHash: enum(HashType)
 machineType: enum(MachineType)
 diskSizeGb: string (int64 format)
 substitutionOption: enum(SubstitutionOption)
 dynamicSubstitutions: boolean
 logStreamingOption: enum(LogStreamingOption)
 logging: enum(LoggingMode)
 pool: object(PoolOption)
substitutions: map (key: string, value: string)
tags: [string, string, ...]
serviceAccount: string
secrets: object(Secret)
availableSecrets: object(Secrets)
artifacts: object (Artifacts)
images:
- [string, string, ...]
```
