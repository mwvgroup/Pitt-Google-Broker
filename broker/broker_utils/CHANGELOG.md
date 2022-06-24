# Changelog<a name="changelog"></a>

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

<!-- uncomment the following when we're out of alpha and actually following it -->

<!-- and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). -->

## \[Unreleased\]<a name="unreleased"></a>

## \[0.2.39\] - 2022-06-23

### Fixed

- Bug fix: don't use `dataclasses.dataclass` decorator on `collections.namedtuple` modules.

## \[0.2.38\] - 2022-06-23

### Added

- Use `dataclasses.dataclass` decorator on `types` and `testing` modules

### Fixed

- Bug fix in `types.AlertIds.extract_ids()`: access `self.id_keys` as a property, not a function call.

## \[0.2.37\] - 2022-06-21

### Changed

- Minor internal improvements and bug fixes to `testing`.
- Rename attributes `testing.Mock.results` to `testing.Mock.module_results` and `testing.TestAlert.publish_as` to `testing.TestAlert.serialize`.

## \[0.2.36\] - 2022-06-20

### Added

- Adds `mock` as a keyword argument in `testing.TestAlert`.

## \[0.2.35\] - 2022-06-20

### Added

- `types` module containing `_AlertIds`, `AlertIds`, and `AlertFilename`. These were rewritten and moved out of `data_utils`.

### Changed

- Lazy load `pandas`. It hogs memory on Cloud Functions.
- Remove `data_utils.AlertIds`, `data_utils.idUtils`, and `data_utils.AlertFilename`. They moved to the new `types` module.
- Rename `tests` module to `testing` and rewrite the included classes to give them more functionality and make them easier to use.

## \[0.2.34\] - 2022-06-17

### Added

- add `AlertFilename` class in `data_utils`

### Changed

- updated `tests.TestValidator` to accept keyword argument `ids_in` that determines whether alert IDs are extracted from message attributes or the Avro filename.

## \[0.2.33\] - 2022-06-17

### Added

- add "kafka.topic" to mocked msg attributes in `tests.TestAlert`

## \[0.2.32\] - 2022-05-19

### Changed

- fix bug when creating avro payload in `tests.TestAlert`

## \[0.2.31\] - 2022-05-19

### Added

- `tests` module and `tests.TestValidator` class
- `data_utils.idUtils` class

### Changed

- moved `data_utils.TestAlert` to `tests.TestAlert`

## \[0.2.30\] - 2022-05-18

### Added

- `data_utils.AlertIds` and `data_utils.TestAlert`
- `gcp_utils.purge_subscription()`

## \[0.2.29\] - 2022-05-17

### Added

- `schema_maps.get_key()` return the key name or the final element in the list corresponding to a schema map and key.
- `schema_maps.get_value()` return the alert value corresponding to a schema map and key.

### Changed

- Modules updated to use the added functions.
- `data_utils.load_yaml()` moved to `schema_maps.load_yaml()` to avoid circular imports.

## \[0.2.28\] - 2022-03-27

### Added

- `math` module - new home for math functions (currently `jd_to_mjd` and `mag_to_flux`)
- `data_utils.load_yaml`

### Changed

- Move functions `jd_to_mjd` and `mag_to_flux` from `data_utils` to the new `math` module. Update SuperNNova Cloud Function to accommodate (outside `broker_utils` at broker/cloud_functions/classify_snn).
- Update `schema_maps.load_schema_map` to accept a Path and load from a local file

### Removed

- `data_utils._get_schema_map`

## \[0.2.27\] - 2022-03-26

### Added<a name="added-1"></a>

- `data_utils._get_schema_map` function to load schema map from file if needed and check that it is a dict.
- `data_utils.load_alert` to load an alert from file.
- Support for passing `alert_avro` as a path to `data_utils.decode_alert`.

### Changed<a name="changed-1"></a>

- `data_utils` now passes `schema_map` and `drop_cutouts` as kwargs.

### Fixed<a name="fixed-1"></a>

- Rename variable `pgb_project_id` to `PROJECT_ID`.

## \[0.2.26\] - 2022-03-26<a name="0226---2022-03-26"></a>

### Added<a name="added"></a>

- Add `project_id` as a kwarg to `gcp_utils` bigquery functions.

### Changed<a name="changed"></a>

- Set GCP project ID by an environment variable, fall back to the production broker project. Formerly this was hardcoded to production project.
- Unpin `numpy`
- Unpin `google.cloud.bigquery`
- Unpin `google.cloud.pubsub`. Update `consumer_sim` and `gcp_utils` to accommodate.
