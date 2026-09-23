# shellcheck shell=bash
# Constants shared by the run scripts, mirroring
# jenkins/common/variables.groovy. Sourced, not executed.

export extpar_input_data=/net/co2/c2sm-data/extpar-input-data/
export https_public_root=/net/co2/c2sm-services/zonda-request/
export n_threads=24
export netcdf_format=NETCDF4
export config_filename=config.json
export hash_filename=hash.txt
export log_filename=zonda_request.log

# Absolute path: non-interactive ssh sessions do not source ~/.bashrc, so
# uv is not on PATH. All Python runs through it to use the synced venv.
export uv="$HOME/.local/bin/uv"
