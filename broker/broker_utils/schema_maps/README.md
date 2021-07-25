# Schema Maps

The files in this directory contain mappings between the schema of an individual survey and a PGB-standardized schema that is used within the broker code.

Note: This directory is __not__ packaged with the `broker_utils` module.
In order to allow broker instances to use unique schema maps, independent of other instances, each instance uploads this directory to its [`broker_files`] Cloud Storage bucket upon setup.
The broker code loads the schema maps from the bucket of the appropriate instance at runtime.
