#!/bin/bash

_usage() {
    echo "Usage: $0 [-s|--stem] <stem> [[-g|--gcp-service] <gcp_service>]"
}

_info() {
    echo "Use '$(basename $0) --help' for more information."
}

_help() {
    echo "Construct the GCP resource name using the supplied options and the env vars SURVEY and TESTID."
    echo
    _usage
    echo
    echo "Options:"
    echo "  -s, --stem <stem>       Name stem for the resource. SURVEY will be prepended and TESTID "
    echo "                          appened (if not false)."
    echo "  -g, --gcp-service <gcp_service>"
    echo "                          Determines the separator. If the value is 'bigquery', the"
    echo "                          separator will be '_'. Otherwise it is '-'."
    echo
    echo "Environment Variables:"
    echo "  SURVEY                  Required. Prepend to resource name."
    echo "  TESTID                  Required. Append to resource name if not 'False'."
}

# Ensure that all required environment variables are set.
check_env_vars() {
  local vars=("$@")
  for var in "${vars[@]}"; do
    if [ -z "${!var}" ]; then
      echo "Error: ${var} environment variable is not set."
      exit 1
    fi
  done
}
check_env_vars SURVEY TESTID

stem=""
gcp_service=""

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -s|--stem)
      stem="$2"
      shift
      shift
      ;;
    -g|--gcp-service)
      gcp_service="$(echo "$2" | tr '[:upper:]' '[:lower:]')"
      shift
      shift
      ;;
    -h|--help)
      _help
      exit 0
      ;;
    *)
      echo "Invalid option: $1"
      _info
      exit 1
      ;;
  esac
done

if [ -z "$stem" ]; then
    echo "Missing required option 'stem'."
    _info
    exit 1
fi

_sep="-"
if [ "$gcp_service" = "bigquery" ]; then
    _sep="_"
fi

_testid="${_sep}${TESTID}"
if [ "$TESTID" = "False" ] || [ "$TESTID" = "false" ]; then
    _testid=""
fi

echo "${SURVEY}${_sep}${stem}${_testid}"
