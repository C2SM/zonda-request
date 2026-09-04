# shellcheck shell=bash
# shellcheck disable=SC2034 # consumed by whichever script sources this file
# Single source of truth for constants shared by run_pipeline.sh,
# process_request.sh and run_testsuite_request.sh. Sourced, not executed.
# Mirrors jenkins/common/variables.groovy.

extpar_input_data=/net/co2/c2sm-data/extpar-input-data/
https_public_root=/net/co2/c2sm-services/zonda-request/
n_threads=24
netcdf_format=NETCDF4
config_filename=config.json
hash_filename=hash.txt
log_filename=zonda_request.log
