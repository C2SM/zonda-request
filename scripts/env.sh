# shellcheck shell=bash
# shellcheck disable=SC2034 # consumed by whichever script sources this file
# Constants shared by the run scripts, mirroring
# jenkins/common/variables.groovy. Sourced, not executed.

extpar_input_data=/net/co2/c2sm-data/extpar-input-data/
https_public_root=/net/co2/c2sm-services/zonda-request/
n_threads=24
netcdf_format=NETCDF4
config_filename=config.json
hash_filename=hash.txt
log_filename=zonda_request.log

# Absolute path: non-interactive ssh sessions do not source ~/.bashrc, so
# uv is not on PATH. All Python runs through it to use the synced venv.
uv="$HOME/.local/bin/uv"
