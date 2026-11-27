# shellcheck shell=bash
# Constants shared by the run scripts. Sourced, not executed.

export EXTPAR_INPUT_DATA=/net/co2/c2sm-data/extpar-input-data/
export N_THREADS=24
export NETCDF_FORMAT=NETCDF4
export CONFIG_FILENAME=config.json
export LOG_FILENAME=zonda_request.log

# Absolute path: non-interactive SSH sessions do not source ~/.bashrc, so
# uv is not on PATH. All Python runs through it to use the synced venv.
export UV="$HOME/.local/bin/uv"

# Concurrency cap shared by all runs on this machine.
export N_SLOTS=6
export SLOTS_DIR="$HOME/.zonda/slots"

# Identity of the Zonda-Bot GitHub App. Not secret; only its private key is.
export ZONDA_APP_ID=4546985
export ZONDA_APP_INSTALLATION_ID=152656376
